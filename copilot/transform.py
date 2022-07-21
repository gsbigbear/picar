import time, cv2
import numpy as np

# stdout print color
def ColorPrint(text,color="blue"): 
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

class copilot_transform(object):
    def __init__(self,cfg) :
        self.on = True 
        self.cfg = cfg
        self.cfg.transformstats = {}
        self.cfg.toolz_transform_global_ms=None

    def shutdown(self) : 
        self.on = False
        self.print_perfmon()

    def update(self):
        ColorPrint("Start - copilot_transform")

    def run_threaded(self,image):        
        start_global=time.time()
        if self.cfg.COPILOT_TRANSFORM :
            for id, transform in enumerate(self.cfg.COPILOT_TRANSFORM_LIST) :
                if self.cfg.COPILOT_TRANSFORM_PERFMON : start_time = time.time()
                image = self.transform_this(image,transform)
                if self.cfg.COPILOT_TRANSFORM_PERFMON and start_time is not None: 
                    if transform not in self.cfg.transformstats: self.cfg.transformstats[transform]=[]
                    self.cfg.transformstats[transform].append(time.time() - start_time)
                    if len(self.cfg.transformstats[transform]) > 200 : self.cfg.transformstats[transform]=self.cfg.transformstats[transform][100:]    
        self.cfg.toolz_transform_global_ms=round((time.time() - start_global)*1000,2)
        return image

    def print_perfmon(self):
        ColorPrint("+--------------------+-----------+")
        ColorPrint("+   Transformation   +  Time(ms) +")
        ColorPrint("+--------------------+-----------+")
        for transform in self.cfg.transformstats : 
            ColorPrint("| {:>18} | {:>9} |".format(transform,round(sum(self.cfg.transformstats[transform])/len(self.cfg.transformstats[transform])*1000,4)))
        ColorPrint("+--------------------+-----------+")

    def transform_this(self,frame,transform):        
        # TRAPEZOID transformation
        def warp(frame):
            IMAGE_H, IMAGE_W = ( frame.shape[0],frame.shape[1] )
            src = np.float32([  [int(IMAGE_W*self.cfg.COPILOT_WARP_PADDING_WIDTH_BACK),int(IMAGE_H*self.cfg.COPILOT_WARP_PADDING_TOP)],
                                [int(IMAGE_W*(1-self.cfg.COPILOT_WARP_PADDING_WIDTH_BACK)), int(IMAGE_H*self.cfg.COPILOT_WARP_PADDING_TOP)],
                                [int(IMAGE_W*(1-self.cfg.COPILOT_WARP_PADDING_WIDTH_FRONT)), int(IMAGE_H*(1-self.cfg.COPILOT_WARP_PADDING_BOTTOM))], 
                                [int(IMAGE_W*self.cfg.COPILOT_WARP_PADDING_WIDTH_FRONT), int(IMAGE_H*(1-self.cfg.COPILOT_WARP_PADDING_BOTTOM))]])
            dst = np.float32(   [[0, 0],
                                [IMAGE_W, 0],
                                [IMAGE_W, IMAGE_H],
                                [0, IMAGE_H]])
            matrix = cv2.getPerspectiveTransform(src,dst)
            frame = cv2.warpPerspective(frame,matrix,(IMAGE_W,IMAGE_H), flags=cv2.INTER_LINEAR)
            return frame

        # cornercut top 
        def cornercut(img):
            imageHeight, imageWidth, imageColorDepth = img.shape
            triangle = np.array([[0, 0], [self.cfg.COPILOT_CORNERCUT_SIDE, 0], [0, self.cfg.COPILOT_CORNERCUT_TOP]])
            cv2.fillConvexPoly(img, triangle, [0, 0, 0])
            triangle = np.array([[imageWidth, 0], [imageWidth - self.cfg.COPILOT_CORNERCUT_SIDE, 0], [imageWidth, self.cfg.COPILOT_CORNERCUT_TOP]])
            cv2.fillConvexPoly(img, triangle, [0, 0, 0])
            return img

        def medianBlur(frame):
            return cv2.medianBlur(frame, 5)

        def reverse(frame):
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            buf = cv2.bitwise_not(frame)
            return cv2.cvtColor(buf, cv2.COLOR_HSV2BGR)
        
        def brightContrast(input_img):
            brightness=self.cfg.COPILOT_BRIGHTNESS
            contrast=self.cfg.COPILOT_CONTRAST
            #Source : https://www.life2coding.com/change-brightness-and-contrast-of-images-using-opencv-python/
            if brightness != 0:
                if brightness > 0:
                    shadow = brightness
                    highlight = 255
                else:
                    shadow = 0
                    highlight = 255 + brightness
                alpha_b = (highlight - shadow)/255
                gamma_b = shadow
                buf = cv2.addWeighted(input_img, alpha_b, input_img, 0, gamma_b)
            else:
                buf = input_img.copy()
            if contrast != 0:
                f = float(131 * (contrast + 127)) / (127 * (131 - contrast))
                alpha_c = f
                gamma_c = 127*(1-f)
                buf = cv2.addWeighted(buf, alpha_c, buf, 0, gamma_c)
            return buf

        def laplacian(img):
            sharpen_filter = np.array(
                [[self.cfg.COPILOT_LAPLACIAN_SHARPEN_DIAG, self.cfg.COPILOT_LAPLACIAN_SHARPEN_CROSS, self.cfg.COPILOT_LAPLACIAN_SHARPEN_DIAG],
                 [self.cfg.COPILOT_LAPLACIAN_SHARPEN_CROSS, self.cfg.COPILOT_LAPLACIAN_SHARPEN_CENTER, self.cfg.COPILOT_LAPLACIAN_SHARPEN_CROSS],
                 [self.cfg.COPILOT_LAPLACIAN_SHARPEN_DIAG, self.cfg.COPILOT_LAPLACIAN_SHARPEN_CROSS, self.cfg.COPILOT_LAPLACIAN_SHARPEN_DIAG]]
                )
            img =  cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            layer = img.copy()
            gp = [layer]
            for i in range(5):
                layer = cv2.pyrDown(layer)
                gp.append(layer)
            layer = gp[5]
            lp = [layer]
            for i in range(5,3-self.cfg.COPILOT_LAPLACIAN_DEPTH,-1):
                guassian_extended = cv2.pyrUp(gp[i])
                laplacian = cv2.subtract(gp[i-1],guassian_extended)          

            sharped_img = cv2.filter2D(laplacian, -1, sharpen_filter)
            blur = cv2.GaussianBlur(sharped_img,(self.cfg.COPILOT_LAPLACIAN_BLUR,self.cfg.COPILOT_LAPLACIAN_BLUR),0)
            thresh = cv2.threshold(blur, self.cfg.COPILOT_LAPLACIAN_THRES_LOW, self.cfg.COPILOT_LAPLACIAN_THRES_HIGH, cv2.THRESH_BINARY)[1]
            return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

        return locals()[transform](frame) 
