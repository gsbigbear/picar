import myconfig as cfg
from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap,QImage,QIcon
from PIL import Image, ImageQt 
from numpy import asarray
import sys, os, glob, re, json, cv2
from copilot.stepcounter import copilot_stepcounter as copilot
from copilot.protoxyde import copilot_protoxyde as protoxyde

remote_path = "pi@picar:/home/pi/picar"
local_path = "/media/bigbear/120-DATA/DonkeyCar/picar"
tub_path = "/media/bigbear/120-DATA/DonkeyCar/picar/data"
model_path = "/media/bigbear/120-DATA/DonkeyCar/picar/models"
archive_path = "/media/bigbear/120-DATA/DonkeyCar/picar/data_back"

if __name__ == "__main__":
    cfg_ori=dict(vars(cfg))
    
    class Ui(QtWidgets.QMainWindow):
        def __init__(self):
            super(Ui, self).__init__()
            uic.loadUi('copilot/ui_copilot.ui', self)
            # vars
            self.img_list=[]                # dictionnaire du tub actuel
            self.img_index=0                # index img du tub
            self.do_after_process=''
            self.current_tub_path=None
            cfg.model_path=None
            self.tf2c = copilot(cfg)
            self.protoxyde = protoxyde(cfg)
            self.report_color={}
            self.tub_dict={}                # manifest
            self.tub_dict_exclude=[]        # manifest

            # Qprocess pour le stdout         
            self.process = QtCore.QProcess(self)
            self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            self.process.readyRead.connect(self.stdout_dataReady)
            self.process.started.connect(lambda: self.processbtn.setEnabled(True))
            self.process.finished.connect(lambda: self.end_process(False)) 
            self.processbtn.setEnabled(False)
            self.processbtn.clicked.connect(lambda: self.end_process(True))

            # path remote / local
            self.textRemote.setPlainText(remote_path)
            self.textLocal.setPlainText(local_path )

            # model + tub
            self.list_tub.itemClicked.connect(self.select_tub)
            self.trainselected.clicked.connect(lambda: self.traintub_action(True))
            self.traintubbtn.clicked.connect(lambda: self.traintub_action(False))
            self.reversetubbtn.clicked.connect(self.reversetub)
            self.pushmodels.clicked.connect(self.pushmodels_action)
            self.makemoviebtn.clicked.connect(self.makemovie_action)
            self.makemoviesmall.clicked.connect(lambda: self.makemovie_action(500))

            # slider play
            self.sliderplay.valueChanged.connect(self.refresh_view)
            self.sliderplay.setMaximum(0)
            self.sliderplay.setMinimum(0)
            self.sliderplay.setValue(0) 
            self.previousbtn.pressed.connect(self.previous_img)
            self.nextbtn.pressed.connect(self.next_img)
            self.previousbtn.setAutoRepeat(True)
            self.nextbtn.setAutoRepeat(True)

            # action
            self.syncmodels.clicked.connect(lambda: self.call_process('rsync',["-r","--progress",remote_path+"/models/",local_path+"/models/"]))
            self.cleansmall.clicked.connect(lambda: self.confirm_process('bash',['-c','du -s  {}/* | while read size filename; do if [ $size -lt 500 ]; then rm -rf "$filename";echo "<500ko $filename" ; fi; done'.format(self.textLocal.toPlainText()+"/data/")]))
            self.tubclean.clicked.connect(lambda: self.call_process('donkey',["tubclean",tub_path]))
            self.syncdata.clicked.connect(lambda: self.call_process('rsync',["-r","--progress",remote_path+"/data/",local_path+"/data/"]))
            self.newtubsession.clicked.connect(lambda: self.confirm_process('bash',['-c','mkdir -p {} && mv {} {} && mv {} {} && mkdir {} && mkdir {}'.format(archive_path,\
                self.textLocal.toPlainText()+"/models",archive_path, local_path+"/data",archive_path,\
                self.textLocal.toPlainText()+"/models",local_path+"/data"
                )]))
            # Refresh list
            self.refresh_tublist()
            self.refresh_modellist() 

            # pixel
            self.benchpixel.clicked.connect(self.run_bench)
            # slider color low
            self.sliderlowR.valueChanged.connect(self.refresh_default)
            self.sliderlowG.valueChanged.connect(self.refresh_default)
            self.sliderlowB.valueChanged.connect(self.refresh_default)
            # slider color up
            self.sliderupR.valueChanged.connect(self.refresh_default)
            self.sliderupG.valueChanged.connect(self.refresh_default)
            self.sliderupB.valueChanged.connect(self.refresh_default)

            # alimentation des filter color
            self.list_filter.clear()
            for color in ["custom"] + [*cfg.COPILOT_COLOR_FILTER] : 
                item = QListWidgetItem(color)
                item.setCheckState(Qt.Checked)
                self.list_filter.addItem(item)
            self.list_filter.setDragDropMode(self.list_filter.InternalMove)
            self.list_filter.itemClicked.connect(self.refresh_default)

            # show UI
            self.show()
        
        def run_bench(self):
            self.stdout_dataReady("Start bench filter color")
            self.report_color={} 
            for i in range(len(self.img_list)):
                self.refresh_view(i)
                if i % 100 == 0 : self.repaint()
                if i > self.spinBoxImg.value(): break
            self.stdout_dataReady("Bench finished ")
            self.print_report_color()
            self.refresh_view(0)

        def traintub_action(self,multi=True):
            if multi:
                folder=self.textLocal.toPlainText()+"/data/"
                tub_list = [folder+self.list_tub.item(index).text() for index in range(self.list_tub.count()) if self.list_tub.item(index).checkState() == Qt.Checked]
            else :
                tub_list = [self.current_tub_path] 
            try:               
                if len(tub_list)==1: 
                    proposition = tub_list[0].replace("/data/","/models/") + ".h5"
                else : 
                    proposition = tub_list[0].replace("/data/","/models/") + "_mixed.h5"
            except:
                QMessageBox.about(self, "Erreur de sélection", "Sélectionner un ou plusieurs tubs !")
                return
            if tub_list :
                target_h5=QtWidgets.QFileDialog.getSaveFileName(self, 'h5 target name',proposition,'*.h5')
                if target_h5 and target_h5[0] != '':
                    target_h5=target_h5[0] if '.h5' in target_h5[0] else target_h5[0]+'.h5'
                    args_list=['train','--model',target_h5,'--type','linear','--tub',','.join(tub_list)]
                    #if self.checkaug.isChecked(): args_list.append("--aug")
                    self.call_process('donkey',args_list)

        def select_tub(self, file_path=None) : 
            self.current_tub_path=tub_path+"/"+file_path.text()
            self.img_list=[f for f in glob.glob('{}/**/*.jpg'.format(self.current_tub_path), recursive=True)]
            self.img_list.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))
            self.sliderplay.setMaximum(len(self.img_list) - 1)
            self.spinBoxImg.setMaximum(len(self.img_list))
            self.spinBoxImg.setValue(len(self.img_list))  
            self.lcdIMG.display(len(self.img_list))
            self.refresh_view(self.img_index)  
            # on tente de loader le dic associé
            self.tub_dict={}
            catalogs=[f for f in glob.glob('{}/catalog_?.catalog'.format(self.current_tub_path), recursive=False)]
            for catalog in catalogs:
                with open(catalog, "r") as fp:
                    Lines = fp.readlines()
                    for line in Lines:
                        data=json.loads(line)
                        self.tub_dict[data['cam/image_array']]=data
            self.tub_dict_exclude=[]
            # dic des exclusions
            self.manifest='{}/manifest.json'.format(self.current_tub_path)
            with open(self.manifest, "r") as fp:
                Lines = fp.readlines()
                for line in Lines:
                    data=json.loads(line)
                    if "deleted_indexes" in data: 
                        self.tub_dict_exclude=data['deleted_indexes']  
                        self.lcdmasked.display(len(self.tub_dict_exclude))
        
        def refresh_default(self):
            self.refresh_view(self.img_index)

        def refresh_view(self,index) : 
            if len(self.img_list) == 0: return
            self.img_index=index
            self.sliderplay.blockSignals(True)
            self.sliderplay.setValue(index)
            self.sliderplay.blockSignals(False)
            self.lcdcurrentimg.display(index+1)
            image = Image.open(self.img_list[index])
            image = asarray(image)
            self.get_filtercolor(image)
            img_key=(self.img_list[self.img_index].split("/")[-1])
            # # ajout des angle/throttle
            if img_key in self.tub_dict:
                data=self.tub_dict[img_key]
                self.lcdthrottle.display( data['user/throttle'])
                self.lcdangle.display(data['user/angle'])
                image=self.draw(image,data['user/angle'],data['user/throttle'])
                # masked or not
                if self.tickvisible.isChecked() :
                    self.change_manifest(data['_index'], remove=True)
                    cv2.line(image, pt1=(0,0), pt2=(160,0), color=(0,255,0), thickness=3)  
                elif self.tickmasqued.isChecked() :
                    self.change_manifest(data['_index'], remove=False)
                    cv2.line(image, pt1=(0,0), pt2=(160,0), color=(255,0,0), thickness=3)  
                elif data['_index'] in self.tub_dict_exclude:
                    cv2.line(image, pt1=(0,0), pt2=(160,128), color=(255,0,0), thickness=2)  
                    cv2.line(image, pt1=(0,128), pt2=(160,0), color=(255,0,0), thickness=2) 
                # protoxyde
                new_angle, new_throttle = self.protoxyde.run_threaded(data['user/angle'],data['user/throttle'])
                style ="QLCDNumber {  color: green; }" if float(self.newthrottle.value()) <= new_throttle else "QLCDNumber {  color: red; }"
                self.newthrottle.display (new_throttle)
                self.newthrottle.setStyleSheet(style)                        
                self.newangle.display(new_angle)

            pixmap = self.image_to_pixmap(image)
            self.frameinput.setScaledContents(True)
            self.frameinput.setPixmap(pixmap) 
        
        def change_manifest(self, _index, remove=True):
            with open(self.manifest, "r") as fp: Lines = fp.readlines()
            with open(self.manifest, "w") as fp:
                for line in Lines:
                    if "deleted_indexes" not in line: fp.write(line)  
                    else:
                        data=json.loads(line)
                        if remove : 
                            if _index in data['deleted_indexes']: data['deleted_indexes'].remove(_index)
                        else: 
                            if _index not in data['deleted_indexes'] : data['deleted_indexes'].append(_index)
                        self.tub_dict_exclude=data['deleted_indexes']
                        self.lcdmasked.display(len(self.tub_dict_exclude))
                        line=json.dumps(data)
                        fp.write(line)  

        def get_filtercolor(self,image_ori):
            self.clearLayout(self.layoutfilterresult)
            vbox = QHBoxLayout()
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(0)
            self.dic_custom={"custom":{"lower":(self.sliderlowR.value(), self.sliderlowG.value(), self.sliderlowB.value()),"upper":(self.sliderupR.value(), self.sliderupG.value(), self.sliderupB.value())}}
            self.filtercustom.setPlainText(json.dumps(self.dic_custom["custom"]))
            dict_color={**self.dic_custom,**cfg.COPILOT_COLOR_FILTER}
            for index in range(self.list_filter.count()):
                if self.list_filter.item(index).checkState() == Qt.Checked:
                    key = self.list_filter.item(index).text()
                    value = dict_color[key]
                    image = image_ori.copy()
                    pixel, mask  = self.tf2c.get_img_info(image,value)
                    if pixel > self.spinBoxPxl.value():
                        if key not in self.report_color: self.report_color[key]={}
                        self.report_color[key][str(self.img_index)]=str(pixel)
                    image = cv2.bitwise_and(image,image,mask=mask)
                    vbox.addLayout(self.build_thumb(key,image,"{}px".format(pixel)))
            self.layoutfilterresult.addLayout(vbox)   


        def next_img(self):
            self.img_index = self.img_index + 1 if self.img_index + 1 < len(self.img_list) else 0
            self.sliderplay.setValue(self.img_index)  

        def previous_img(self):
            self.img_index = self.img_index - 1 if self.img_index > 0 else len(self.img_list)-1
            self.sliderplay.setValue(self.img_index)

        def refresh_modellist(self):
            self.list_model.clear()
            folder=self.textLocal.toPlainText()+"/models/"
            for path in  [ f.path for f in os.scandir(folder) if os.path.isfile(f) and 'myconfig' not in str(f) and ('.h5' in str(f) or '.tflite' in str(f))  ] : 
                item = QListWidgetItem(path.replace(folder,''))
                item.setCheckState(Qt.Unchecked)
                self.list_model.addItem(item)
            self.list_model.itemClicked.connect(self.show_model_config)
        
        def show_model_config(self,value):
            config_path=self.textLocal.toPlainText()+"/models/" + value.text() 
            self.modelpng.clear()
            if os.path.isfile(config_path + ".myconfig") :
                with open(config_path+ ".myconfig") as file: lines = [line.strip() for line in file]
                self.configinfo.setPlainText("\n".join(lines))   
            if '.h5' in config_path:img_path=config_path.replace('.h5',".png")
            else:img_path=config_path.replace('.tflite',".png")
            if os.path.isfile(img_path) : 
                image = Image.open(img_path)
                image = asarray(image)
                self.modelpng.setPixmap(self.image_to_pixmap(image))


        def refresh_tublist(self):
            self.list_tub.clear()
            folder=self.textLocal.toPlainText()+"/data/"
            for path in  [ f.path for f in os.scandir(folder) if f.is_dir() ] : 
                item = QListWidgetItem(path.replace(folder,''))
                item.setCheckState(Qt.Unchecked)
                self.list_tub.addItem(item)
        
        def reversetub(self):
            source_tub = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select tub Folder source', self.current_tub_path)
            target_tub = QtWidgets.QFileDialog.getExistingDirectory (self ,'Select tub folder target',tub_path)
            if source_tub and target_tub :
                self.stdout_dataReady("Duplication de la directory")
                os.system("mkdir -p {}/images".format(target_tub))
                os.system("cp -r {}/* {}".format(source_tub,target_tub))
                self.stdout_dataReady("Reconstruction json")
                catalogs=[f for f in glob.glob('{}/catalog_?.catalog'.format(target_tub), recursive=False)]
                for catalog in catalogs:
                    if 'manifest' in catalog : continue
                    with open(catalog, "r") as fp: Lines = fp.readlines() # load 
                    with open(catalog, "w") as fp: #rebuild 
                        for i, line in enumerate(Lines):
                            if i % 100 : 
                                self.stdout_dataReady("Process img : {}/{}".format(i+1,len(Lines)))
                                self.repaint()
                            data=json.loads(line)
                            # reverse angle
                            data['user/angle']=-data['user/angle']
                            line=json.dumps(data)
                            fp.write(line+"\n")
                            # process image
                            image_path='{}/images/{}'.format(target_tub,data["cam/image_array"])
                            originalImage = cv2.imread(image_path)
                            flipHorizontal = cv2.flip(originalImage, 1)
                            cv2.imwrite(image_path,flipHorizontal)
                self.stdout_dataReady("Fin du traitement")
        
        def makemovie_action(self,limit=False):
            try:
              first_checked_model = [tub_path+"/"+self.list_model.item(index).text() for index in range(self.list_model.count()) if self.list_model.item(index).checkState() == Qt.Checked][0]
              first_checked_tub = [model_path+"/"+self.list_tub.item(index).text() for index in range(self.list_tub.count()) if self.list_tub.item(index).checkState() == Qt.Checked][0]
            except:
              QMessageBox.about(self, "Erreur de sélection", "Sélectionner 1 model et 1 tub !")
              return False
            target_mp4=QtWidgets.QFileDialog.getSaveFileName(self, 'mp4 out file',local_path,'*.mp4')
            if target_mp4 and target_mp4[0] != '':
                target_mp4=target_mp4[0] if '.mp4' in target_mp4[0] else target_mp4[0]+'.mp4'
                type_model='linear' if '.h5' in first_checked_model else 'tflite_linear'
                if limit == False:
                    self.confirm_process('donkey',['makemovie','--tub',first_checked_tub,'--model',first_checked_model,'--out',target_mp4,'--type',type_model])
                else :
                    self.confirm_process('donkey',['makemovie','--tub',first_checked_tub,'--model',first_checked_model,'--out',target_mp4,'--type',type_model,'--start','0','--end','500'])
                    self.do_after_process="parole {}".format(target_mp4)

        def pushmodels_action(self):
            checked_models_list = [model_path+"/"+self.list_model.item(index).text() for index in range(self.list_model.count()) if self.list_model.item(index).checkState() == Qt.Checked]
            for models in checked_models_list :
                self.confirm_process('bash',['-c','scp {} {} && echo push OK'.format(models.replace('.h5','.*'),remote_path+"/models/")])

        def confirm_process(self,binary,args_list):
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("{}\n{}".format(binary,args_list))
            msgBox.setWindowTitle("Confirmation")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                self.call_process(binary,args_list)

        def call_process(self,binary,args_list):
            self.stdout_dataReady("Start command : {},{}".format(binary,args_list))
            print("{} {}".format(binary,' '.join(args_list)))
            self.process.start(binary, args_list)
        
        def end_process(self, forced=False):
            self.processbtn.setEnabled(False)
            if forced: 
                self.process.kill()
                self.stdout_dataReady("\nBreak Task")
            else:
                self.stdout_dataReady("\nEnd Task")
            if self.do_after_process:
                os.system(self.do_after_process)
                self.do_after_process = False
            self.refresh_tublist()
            self.refresh_modellist()

        def print_report_color(self):
            self.listpixelmatch.clear()
            self.listpixelmatch.setHeaderLabels(('id', 'pixel'))
            for key,value in self.report_color.items() :
                parent_it = QtWidgets.QTreeWidgetItem(["{}({})".format(key,len(value))])
                self.listpixelmatch.addTopLevelItem(parent_it)
                for id,pixel in value.items() : 
                    it = QtWidgets.QTreeWidgetItem([id,pixel])
                    parent_it.addChild(it)
            self.report_color={}

        def stdout_dataReady(self,text=None):
            cursor = self.stdout.textCursor()
            cursor.movePosition(cursor.End)
            if text == None :
                text = str(self.process.readAll().data().decode())
                text = re.sub(r'[\u0080-\uFFFF]+', '_', text).replace('\b','') # drop des backspace
                cursor.insertText(str(text))
            else :
                cursor.insertText(str(text)+"\n")
            self.stdout.ensureCursorVisible()

        def image_to_pixmap(self,image):
            qformat = QImage.Format_Indexed8
            if len(image.shape) == 3:
                if(image.shape[2]) == 4:
                    qformat = QImage.Format_RGBA8888
                else:
                    qformat = QImage.Format_RGB888
            qimage = QImage(image, image.shape[1], image.shape[0], image.strides[0], qformat)          
            pixmap = QPixmap.fromImage(qimage)
            return pixmap

        def clearLayout(self,layout):
            if layout is not None:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget() is not None:
                        child.widget().deleteLater()
                    elif child.layout() is not None:
                        self.clearLayout(child.layout())

        def build_thumb(self,text1,image,text2):
            subbox = QGridLayout()
            if text1 != '' :
                itm = QLabel()
                itm.setText(text1)
                subbox.addWidget(itm)
            itm = QLabel()
            itm.setPixmap(self.image_to_pixmap(image).scaled(300, 300, Qt.KeepAspectRatio, Qt.FastTransformation))
            subbox.addWidget(itm)
            if text2 != '' :                
                itm = QLabel()
                itm.setText(text2)
                subbox.addWidget(itm)
            return subbox
        
        #https://www.hackster.io/weiyupeng23/visualization-debugging-tool-for-auto-driving-789351
        def draw(self,img, angle, throttle, angle_size = 0.1, throttle_size = 0.1):
            if abs(angle) > 1 or throttle > 1 or throttle < 0:
                print('Error input is not correct' + str(angle), '  ' +str(throttle))
                angle = throttle = 0
            #if angle<0:                 print(1)
            #print(img.shape)
            y = img.shape[0]
            x = img.shape[1]
            #define color
            color_arr = [(0,0,0),(51, 153, 51),(0, 204, 0),(0, 204, 0),(102, 255, 51),(153, 255, 51),(204, 255, 51),(255, 255, 0),(255, 153, 0),(204, 51, 0),(255, 0, 0)]
            #define rectangle for angle
            ax0, ay0 , ax1 , ay1 = int(x*0.1), int(y *0.8), int(x*0.9), int(y *0.9)
            ax_length = int((ax1-ax0)/20)
            ax_central = int(ax0+10*ax_length)
            direction = -1 if angle<0 else 1
            val = abs(angle)
            idx = 1   
            while val*10 > idx:
                cv2.rectangle(img, (int(ax_central + (idx-1) *ax_length*direction) , ay0) , (int(ax_central + idx*ax_length*direction) , ay1), color_arr[idx][::-1], thickness=-1)
                idx = idx + 1
            offset = (val*10 - (idx-1) )
            if offset > 0 :
                cv2.rectangle(img, (int(ax_central + (idx-1)*ax_length*direction) , ay0) , (int(ax_central + (idx-1+offset)*ax_length*direction) , ay1), color_arr[idx][::-1], thickness=-1)
            cv2.rectangle(img, (ax0, ay0) , (ax0+20*ax_length , ay1), (255,255,255), thickness=1)
            #define rectangle for throttle
            tx0, ty0, tx1, ty1 = int(x*0.9), int(y *0.7), int(x*0.95), int(y *0.2)
            ty_length = int((ty0-ty1)/10)
            val = throttle
            idx = 1
            while val*10 > idx:
                cv2.rectangle(img, (tx0, ty0 - ((idx-1) * ty_length)) , (tx1, ty0 - (idx * ty_length) ), color_arr[idx][::-1], thickness=-1)
                idx = idx + 1   
            offset = val*10 - (idx-1) 
            if offset > 0 :
                cv2.rectangle(img, (tx0, ty0 - ((idx-1) * ty_length)) , (tx1, int(ty0 - ((idx - 1 + offset)) * ty_length) ), color_arr[idx][::-1], thickness=-1)
            cv2.rectangle(img, (tx0, ty0) , (tx1, ty0 - 10*ty_length ), (255,255,255), thickness=1)
            return img

    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    app.exec_()