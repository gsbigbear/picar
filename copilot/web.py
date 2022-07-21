#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 24 20:10:44 2017
@author: wroscoe
remotes.py
The client and web server needed to control a car remotely.
"""


import os, copy, glob , importlib, sys
import json
import logging
import time
import asyncio

import requests
from tornado.ioloop import IOLoop
from tornado.web import Application, RedirectHandler, StaticFileHandler, RequestHandler
from tornado.httpserver import HTTPServer
import tornado.gen
import tornado.websocket
from socket import gethostname

try :
    from ... import utils
except:
    import donkeycar.utils as utils

logger = logging.getLogger(__name__)

class LocalWebController(tornado.web.Application):

    def __init__(self, port=8887, mode='user',cfg=None):
        '''
        Create and publish variables needed on many of
        the web handlers.
        '''

        print('Starting Donkey Server...', end='')

        this_dir = os.path.dirname(os.path.realpath(__file__))
        self.static_file_path = os.path.join(this_dir, 'templates', 'static')
        self.angle = 0.0
        self.throttle = 0.0
        self.mode = mode
        self.mode_latch = None
        self.recording = False
        self.recording_latch = None
        self.port = port

        self.num_records = 0
        self.wsclients = []
        self.loop = None
        
        global fullcfg
        self.cfg = cfg
        fullcfg = self.cfg

        fullcfg.KEYTOBACKUP =['COPILOT_TRANSFORM_LIST','COPILOT_ENABLE','COPILOT_HW_INFO','COPILOT_TRANSFORM','COPILOT_TRANSFORM_PERFMON',\
        'COPILOT_LAPLACIAN_BLUR','COPILOT_LAPLACIAN_THRES_LOW','COPILOT_LAPLACIAN_THRES_HIGH','COPILOT_LAPLACIAN_DEPTH','COPILOT_LAPLACIAN_SHARPEN',\
        'COPILOT_WARP_PADDING_TOP','COPILOT_WARP_PADDING_BOTTOM','COPILOT_WARP_PADDING_WIDTH_BACK','COPILOT_WARP_PADDING_WIDTH_FRONT',\
        'COPILOT_CORNERCUT_SIDE','COPILOT_CORNERCUT_TOP',\
        'COPILOT_BRIGHTNESS','COPILOT_CONTRAST','COPILOT_PROTOXYDE','COPILOT_PROTOXYDE_THROTTLE_MULT','COPILOT_PROTOXYDE_ACCELERATION','COPILOT_PROTOXYDE_DECELERATION',\
        'COPILOT_PROTOXYDE_NB_SAMPLE','COPILOT_PROTOXYDE_COEFF_MAX','COPILOT_PROTOXYDE_THRESHOLD_HIGH','COPILOT_PROTOXYDE_THRESHOLD_LOW','COPILOT_PROTOXYDE_ANGLE_LOW_COEF',\
        'COPILOT_PROTOXYDE_THROTTLE_MIN','COPILOT_LAPLACIAN_SHARPEN_CENTER','COPILOT_LAPLACIAN_SHARPEN_DIAG','COPILOT_LAPLACIAN_SHARPEN_CROSS']
        fullcfg.confui_path = os.path.dirname(os.path.realpath(__file__)) + "/uiconfig"
        fullcfg.confui_list=[os.path.basename(x).replace(".py","") for x in ['myconfig'] + glob.glob(fullcfg.confui_path+"/*")  if not os.path.isdir(x)]
        fullcfg.confui_profile=None
        fullcfg.confui_model = None
        fullcfg.confui_name="myconfig"
        sys.path.append(fullcfg.confui_path)

        global oricfg
        oricfg = copy.copy(fullcfg)

        # load de la config default
        if 'default' in fullcfg.confui_list:
            print("Load custom config {}".format('default.py'))
            fullcfg.confui_name='default'
            new_cfg =  importlib.import_module('default')
            for k, v in vars(new_cfg).items():
                setattr(fullcfg, k, v)

        # load de la config custom model
        if fullcfg.model_path != None :
            fullcfg.confui_model = fullcfg.model_path
            probable_config=os.path.split(fullcfg.model_path)[-1].replace(".h5","").replace(".tflite","")
            fullcfg.confui_name=probable_config
            if probable_config in fullcfg.confui_list:
                print("Load custom config {}".format(probable_config))
                new_cfg =  importlib.import_module(probable_config)
                for k, v in vars(new_cfg).items():
                    setattr(fullcfg, k, v)
            else:
                print("No custom config {}.py".format(probable_config))

        handlers = [
            (r"/", RedirectHandler, dict(url="/drive")),
            (r"/drive", DriveAPI),
            (r"/wsDrive", WebSocketDriveAPI),
            (r"/wsCalibrate", WebSocketCalibrateAPI),
            (r"/calibrate", CalibrateHandler),
            (r"/video", VideoAPI),
            (r"/debug", debug),
            (r"/wsTest", WsTest),

            (r"/static/(.*)", StaticFileHandler,
             {"path": self.static_file_path}),
        ]

        settings = {'debug': True}
        super().__init__(handlers, **settings)
        print("... you can now go to {}.local:{} to drive "
              "your car.".format(gethostname(), port))

    def update(self):
        ''' Start the tornado webserver. '''
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.listen(self.port)
        self.loop = IOLoop.instance()
        self.loop.start()

    def update_wsclients(self, data):
        print(data)
        if data:
            for wsclient in self.wsclients:
                try:
                    data_str = json.dumps(data)
                    logger.debug(f"Updating web client: {data_str}")
                    wsclient.write_message(data_str)
                except Exception as e:
                    logger.warn("Error writing websocket message", exc_info=e)
                    pass

    def run_threaded(self, img_arr=None, num_records=0, mode=None, recording=None):
        """
        :param img_arr: current camera image or None
        :param num_records: current number of data records
        :param mode: default user/mode
        :param recording: default recording mode
        """
        self.img_arr = img_arr
        self.num_records = num_records

        #
        # enforce defaults if they are not none.
        #
        changes = {}
        if mode is not None and self.mode != mode:
            self.mode = mode
            changes["driveMode"] = self.mode
        if self.mode_latch is not None:
            self.mode = self.mode_latch
            self.mode_latch = None
            changes["driveMode"] = self.mode
        if recording is not None and self.recording != recording:
            self.recording = recording
            changes["recording"] = self.recording
        if self.recording_latch is not None:
            self.recording = self.recording_latch;
            self.recording_latch = None;
            changes["recording"] = self.recording;

        # Send record count to websocket clients
        if (self.num_records is not None and self.recording is True):
            if self.num_records % 10 == 0:
                changes['num_records'] = self.num_records

        # if there were changes, then send to web client
        if changes and self.loop is not None:
            logger.debug(str(changes))
            self.loop.add_callback(lambda: self.update_wsclients(changes))

        return self.angle, self.throttle, self.mode, self.recording

    def run(self, img_arr=None, num_records=0, mode=None, recording=None):
        return self.run_threaded(img_arr, num_records, mode, recording)

    def shutdown(self):
        pass


class DriveAPI(RequestHandler):

    def get(self):
        data = {key:val for key, val in vars(fullcfg).items() if 'COPILOT_' in key or "confui" in key }
        self.render("templates/vehicle.html", **data, all_dic=data)

    def post(self):
        '''
        Receive post requests as user changes the angle
        and throttle of the vehicle on a the index webpage
        '''
        data = tornado.escape.json_decode(self.request.body)

        self.application.angle = data['angle']
        self.application.throttle = data['throttle']
        self.application.mode = data['drive_mode']
        self.application.recording = data['recording']


class WsTest(RequestHandler):
    def get(self):
        data = {}
        self.render("templates/wsTest.html", **data)


class CalibrateHandler(RequestHandler):
    """ Serves the calibration web page"""
    async def get(self):
        await self.render("templates/calibrate.html")


class WebSocketDriveAPI(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        print("New client connected")
        self.application.wsclients.append(self)

    def on_message(self, message):
        data = json.loads(message)
        print('Data {}'.format(data))
        
        self.application.angle = data.get('angle', self.application.angle)
        self.application.throttle = data.get('throttle', self.application.throttle)
        if data.get('drive_mode') is not None:
            self.application.mode = data['drive_mode']
            self.application.mode_latch = self.application.mode
        if data.get('recording') is not None:
            self.application.recording = data['recording']
            self.application.recording_latch = self.application.recording
        for key, val in data.items():
            if 'COPILOT_' in key :                
                setattr(fullcfg, key, val)
            elif key == 'loadconfig':
                if val == 'myconfig':
                    for k, v in vars(oricfg).items():
                        if k in fullcfg.KEYTOBACKUP :
                            setattr(fullcfg, k, v)
                else:
                    sys.path.append(fullcfg.confui_path)
                    new_cfg =  importlib.import_module(val.replace(".py",""))
                    for k, v in vars(new_cfg).items():
                        if k in fullcfg.KEYTOBACKUP:
                            setattr(fullcfg, k, v)
                    fullcfg.confui_name=val

            elif key == 'saveconfig' and val != None:
                text=[]
                for k, v in vars(fullcfg).items():
                    if k in fullcfg.KEYTOBACKUP :
                        if "PATH" in k: # dirty 
                            text.append('{}="{}"'.format(k,v))
                        else:
                            text.append('{}={}'.format(k,v))
                with open(fullcfg.confui_path+"/{}.py".format(val), "w") as file: 
                    file.write('\n'.join(text))
                if val not in fullcfg.confui_list:
                    fullcfg.confui_list.append(val)    

    def on_close(self):
        # print("Client disconnected")
        self.application.wsclients.remove(self)


class WebSocketCalibrateAPI(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        print("New client connected")

    def on_message(self, message):
        print(f"wsCalibrate {message}")
        data = json.loads(message)
        if 'throttle' in data:
            print(data['throttle'])
            self.application.throttle = data['throttle']

        if 'angle' in data:
            print(data['angle'])
            self.application.angle = data['angle']

        if 'config' in data:
            config = data['config']
            if self.application.drive_train_type == "PWM_STEERING_THROTTLE" \
                or self.application.drive_train_type == "I2C_SERVO":
                if 'STEERING_LEFT_PWM' in config:
                    self.application.drive_train['steering'].left_pulse = config['STEERING_LEFT_PWM']

                if 'STEERING_RIGHT_PWM' in config:
                    self.application.drive_train['steering'].right_pulse = config['STEERING_RIGHT_PWM']

                if 'THROTTLE_FORWARD_PWM' in config:
                    self.application.drive_train['throttle'].max_pulse = config['THROTTLE_FORWARD_PWM']

                if 'THROTTLE_STOPPED_PWM' in config:
                    self.application.drive_train['throttle'].zero_pulse = config['THROTTLE_STOPPED_PWM']

                if 'THROTTLE_REVERSE_PWM' in config:
                    self.application.drive_train['throttle'].min_pulse = config['THROTTLE_REVERSE_PWM']

            elif self.application.drive_train_type == "MM1":
                if ('MM1_STEERING_MID' in config) and (config['MM1_STEERING_MID'] != 0):
                        self.application.drive_train.STEERING_MID = config['MM1_STEERING_MID']
                if ('MM1_MAX_FORWARD' in config) and (config['MM1_MAX_FORWARD'] != 0):
                        self.application.drive_train.MAX_FORWARD = config['MM1_MAX_FORWARD']
                if ('MM1_MAX_REVERSE' in config) and (config['MM1_MAX_REVERSE'] != 0):
                    self.application.drive_train.MAX_REVERSE = config['MM1_MAX_REVERSE']

    def on_close(self):
        print("Client disconnected")


class debug(RequestHandler):
    async def get(self):
        data = {key:val for key, val in vars(fullcfg).items() if 'toolz' in key }
        result={"html":''}
        last_id=None
        for key,value in data.items() :
            id = key.split("_")[1]
            if "config" in id: continue
            if id != last_id:
                if id == 'transform' and not fullcfg.COPILOT_TRANSFORM: continue
                if id == 'stepcounter' and not fullcfg.COPILOT_STEPCOUNTER: continue
                if id == 'ina219' and not fullcfg.COPILOT_HW_INFO: continue
                if last_id != None:result['html']+='</div>'
                result['html']+='<center><label style="width:100%;"><span style="float:left;">٩(●̮̮̃•̃)۶</span>{}<span style="float:right;">٩(●̮̮̃•̃)۶</span></label></center><div class="btn-group-xs">'.format(id)
            result['html']+='<button type="button" class="btn btn-lg" style="width:100%;">{}&nbsp;&nbsp;<span class="badge badge-light" >{}</span></button>'.format(key.split("_")[-1],value)
            last_id = id
        result['html']+='</div>'

        if fullcfg.toolz_stepcounter_status and fullcfg.toolz_stepcounter_status == "End race":
            result['report']='<div class="row">'
            # chrono step
            result['report']+='<div class="col-md-6"><h3>Chrono Step</h3><table class="table table-striped">'
            result['report']+='<thead><tr><th  scope="col">{}</th><th scope="col">{}</th><th scope="col">{}</th><tr></thead><tbody>'.format("idx","lap","Time (sec)")
            total=0
            for lap in fullcfg.chrono : 
                if lap !=0: total+=fullcfg.chrono[lap]
                result['report']+='<tr><th scope="row">{}</td><td>{}</td><td>{}</td><tr>'.format(lap,fullcfg.COPILOT_STEPS[lap],round(fullcfg.chrono[lap],4))
            result['report']+='<tr class="table-secondary" ><td >-</td><td>total</td><td>{}</td><tr>'.format(round(total,4))
            result['report']+="</tbody></table></div>"
            # transform time
            result['report']+='<div class="col-md-6"><h3>Transform Time</h3><table class="table table-striped">'
            result['report']+='<thead><tr><th  scope="col">{}</th><th scope="col">{}</th><tr></thead><tbody>'.format("Transform","Time (ms)")
            total=0
            for transform in fullcfg.transformstats : 
                total+=round(sum(fullcfg.transformstats[transform])/len(fullcfg.transformstats[transform])*1000,4)
                result['report']+='<tr><th scope="row">{}</td><td>{}</td><tr>'.format(transform,round(sum(fullcfg.transformstats[transform])/len(fullcfg.transformstats[transform])*1000,4))
            result['report']+='<tr class="table-secondary" ><th scope="row" >total</th><td>{}</td><tr>'.format(round(total,4))
            result['report']+="</tbody></table></div>"
            result['report']+="</div>"
            fullcfg.toolz_stepcounter_status="End race..."       
        self.write(result)


class VideoAPI(RequestHandler):
    '''
    Serves a MJPEG of the images posted from the vehicle.
    '''

    async def get(self):

        self.set_header("Content-type",
                        "multipart/x-mixed-replace;boundary=--boundarydonotcross")

        served_image_timestamp = time.time()
        my_boundary = "--boundarydonotcross\n"
        while True:

            interval = .1
            if served_image_timestamp + interval < time.time() and \
                    hasattr(self.application, 'img_arr'):

                img = utils.arr_to_binary(self.application.img_arr)
                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img))
                self.write(img)
                served_image_timestamp = time.time()
                try:
                    await self.flush()
                except tornado.iostream.StreamClosedError:
                    pass
            else:
                await tornado.gen.sleep(interval)

class BaseHandler(RequestHandler):
    """ Serves the FPV web page"""
    async def get(self):
        data = {}
        await self.render("templates/base_fpv.html", **data)


class WebFpv(Application):
    """
    Class for running an FPV web server that only shows the camera in real-time.
    The web page contains the camera view and auto-adjusts to the web browser
    window size. Conjecture: this picture up-scaling is performed by the
    client OS using graphics acceleration. Hence a web browser on the PC is
    faster than a pure python application based on open cv or similar.
    """

    def __init__(self, port=8890):
        self.port = port
        this_dir = os.path.dirname(os.path.realpath(__file__))
        self.static_file_path = os.path.join(this_dir, 'templates', 'static')

        """Construct and serve the tornado application."""
        handlers = [
            (r"/", BaseHandler),
            (r"/video", VideoAPI),
            (r"/static/(.*)", StaticFileHandler,
             {"path": self.static_file_path})
        ]

        settings = {'debug': True}
        super().__init__(handlers, **settings)
        print("Started Web FPV server. You can now go to {}.local:{} to "
              "view the car camera".format(gethostname(), self.port))

    def update(self):
        """ Start the tornado webserver. """
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.listen(self.port)
        IOLoop.instance().start()

    def run_threaded(self, img_arr=None):
        self.img_arr = img_arr

    def run(self, img_arr=None):
        self.img_arr = img_arr

    def shutdown(self):
        pass


