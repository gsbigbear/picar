import cv2, time, threading, os
import numpy as np

# stdout print color
def ColorPrint(text,color="green"): 
    if color == 'red': print("\033[91m{}\033[00m" .format(text))
    elif color == 'blue': print("\033[94m{}\033[00m" .format(text))
    elif color == 'green': print("\033[92m{}\033[00m" .format(text))
    elif color == 'yellow': print("\033[93m{}\033[00m" .format(text))
    elif color == 'lightPurple': print("\033[94m{}}\033[00m" .format(text))
    elif color == 'purple': print("\033[95m{}\033[00m" .format(text))
    elif color == 'cyan': print("\033[96m{}\033[00m" .format(text))
    elif color == 'lightGray': print("\033[97m{}\033[00m" .format(text))
    elif color == 'black': print("\033[98m{}\033[00m" .format(text))  
    else : print("{}" .format(text))  

class copilot_stepcounter(object):
    def __init__(self,cfg) :
        self.on = True 
        self.cfg = cfg
        self.cfg.stepper_img = None
        self.image = None
        self.ack = True
        self.cfg.chrono={}
        self.timeref=0
        self.cfg.toolz_stepcounter_step=None
        self.cfg.toolz_stepcounter_label=None
        self.cfg.toolz_stepcounter_filter=None
        self.cfg.toolz_stepcounter_pixel=None
        self.cfg.toolz_stepcounter_status="Ready" if self.cfg.model_path else "No model"            

    def shutdown(self) : 
        self.on = False
        self.print_chrono()

    def update(self) :
        ColorPrint("Start - copilot_stepcounter")

        # controle des steps si model present
        if not self.cfg.model_path : 
            ColorPrint("No model ->  no coPilot !")    
        else :
            # controle des steps
            ColorPrint("CoPilot running !")
            loop = 0 if self.cfg.COPILOT_AUTOSTART else 1            
            last_state = False
            while True :
                if self.cfg.COPILOT_STEPCOUNTER == False : 
                    if last_state :
                        ColorPrint("coPilot disable by config! COPILOT_STEPCOUNTER={}!".format(self.cfg.COPILOT_STEPCOUNTER))    
                        last_state=False
                elif loop == 0 :
                    self.playsound(self.cfg.COPILOT_AUDIO_ACTION['init'],1)
                    self.stepcontrol()
                    loop = 1
                elif self.cfg.COPILOT_STEPCOUNTER == None: 
                    self.cfg.COPILOT_STEPCOUNTER = True
                    loop = 0
                time.sleep(1)

    def stepcontrol(self):
        for stepID, step in enumerate(self.cfg.COPILOT_STEPS):
            self.timeref=time.time()
            step_cfg = {**self.cfg.COPILOT_STEPS_CONFIG['default'], **self.cfg.COPILOT_STEPS_CONFIG[step]} 
            self.cfg.toolz_stepcounter_status="Waiting..."
            ColorPrint("Waiting {} secs".format(step_cfg['waitBefore']))
            time.sleep(step_cfg['waitBefore'])
            ColorPrint("Searching {} {} ...".format(step_cfg['pxl_raw'],step_cfg['colorRange']))
            self.cfg.toolz_stepcounter_step= stepID
            self.cfg.toolz_stepcounter_label= step
            self.cfg.toolz_stepcounter_filter= step_cfg['colorRange']            
            self.cfg.toolz_stepcounter_status="Searching..."
            while True:
                if self.cfg.COPILOT_STEPCOUNTER == None: break
                current, image = self.get_img_info(self.image,self.cfg.COPILOT_COLOR_FILTER[step_cfg['colorRange']],step_cfg['crop_region'])
                self.cfg.toolz_stepcounter_pixel=current
                self.cfg.stepper_img = image
                if current > step_cfg['pxl_raw'] or (self.cfg.COPILOT_SKIP_GREEN and stepID == 0): 
                    self.cfg.chrono[stepID]=time.time() - self.timeref
                    self.timeref=time.time()
                    ColorPrint("Step {} Ok, {} < {}, {}".format(stepID, step_cfg['pxl_raw'], current, step_cfg['colorRange']))
                    if self.cfg.COPILOT_STEPCOUNTER_AUDIO : 
                        if stepID == len(self.cfg.COPILOT_STEPS) - 1 :
                            self.playsound(self.cfg.COPILOT_AUDIO_ACTION['end'],1)
                        elif stepID == 0 :
                            self.playsound(self.cfg.COPILOT_AUDIO_ACTION['start'],1)
                        else :
                            self.playsound(self.cfg.COPILOT_AUDIO_ACTION['lap'],stepID)                            
                    self.usermode= step_cfg['race_state']
                    self.ack = False
                    break
                time.sleep(step_cfg['freq_loop'])
            if self.cfg.COPILOT_STEPCOUNTER == None: break
        self.cfg.toolz_stepcounter_status="End race"
        self.usermode= 'user'
        self.ack = False
        ColorPrint("End Race ...")        
 
    def run_threaded(self,image, usermode):
        self.image = image
        if self.ack == False:
            self.ack = True            
            usermode = self.usermode               
        return usermode

    def print_chrono(self):
        total=0
        ColorPrint("+-----+-------------+------------+")
        ColorPrint("| {:>3} | {:>11} | {:>10} |".format("idx","lap","Time(sec)"))
        ColorPrint("+-----+-------------+------------+")
        for lap in self.cfg.chrono : 
            if lap !=0: total+=self.cfg.chrono[lap]
            ColorPrint("| {:>3} | {:>11} | {:>10} |".format(lap,self.cfg.COPILOT_STEPS[lap],round(self.cfg.chrono[lap],4)))
        ColorPrint("+-----+-------------+------------+")
        ColorPrint("| {:>3} | {:>11} | {:>10} |".format("-","race",round(total,4)))
        ColorPrint("+-----+-------------+------------+")


    # Retourne le nb de pixel qui matchent le color filter et la frame 
    def get_img_info(self,frame,colordict,crop_region='all'):
        if crop_region != 'all': frame = self.crop_image(frame,self.cfg.COPILOT_CROP_REGION[crop_region])  
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_hsv = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(img_hsv, np.array(colordict['lower']),np.array(colordict['upper']))        
        kernel = np.ones((7,7),np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        conts,h=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        result = np.sum(mask)
        return result, mask 
    
    # crop de l'image
    def crop_image(self,frame,crop_region):
        height, width, _ = frame.shape
        cropped_img = frame[int(crop_region[0]*height):int(crop_region[1]*height),int(crop_region[2]*width):int(crop_region[3]*width)]
        return cropped_img

    def play_audio(self,dictplay,loop):
        dictplay['loop']=loop
        try:
            cmd = "mplayer -ao alsa:device=hw=1.0 -loop {loop} -af volume={volume}:1 {title} -ss {startpos} -endpos {timetoplay} > /dev/null 2>&1 ".format(**dictplay)
            result = os.system(cmd)
        except:
            pass

    def playsound(self,dictplay,loop=1):
        thread = threading.Thread(target=self.play_audio, args=(dictplay,loop,))
        thread.start()
