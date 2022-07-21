import time
# stdout print color
def ColorPrint(text,color="red"): 
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


class copilot_protoxyde(object):
    """ Accélération en ligne droite et décélération dans les virages
    """
    def __init__(self,cfg):
        self.cfg=cfg
        self.protoxyde_coeff=self.cfg.COPILOT_PROTOXYDE_THROTTLE_MULT      # par défaut pas de changement
        self.angle_history = []        
        self.angle = None
        self.throttle = None

    def shutdown(self):
        pass
    def run(self,angle,throttle):
        return self.run_threaded(angle,throttle)

    def run_threaded(self,angle, throttle):
        #self.cfg=cfgProtoxyde
        if self.cfg.COPILOT_PROTOXYDE is not True: 
            return angle, throttle
        if not throttle or throttle < 0: return angle, throttle
        self.angle_history.append(angle) 
        self.angle = angle
        self.throttle = throttle
        # sample rotate
        if len (self.angle_history) >= self.cfg.COPILOT_PROTOXYDE_NB_SAMPLE:
            self.angle_history=self.angle_history[-self.cfg.COPILOT_PROTOXYDE_NB_SAMPLE:]
        mean = abs(sum(self.angle_history)/len(self.angle_history))

        if abs(mean) > self.cfg.COPILOT_PROTOXYDE_THRESHOLD_HIGH:
            # décélération
            self.protoxyde_coeff -= self.cfg.COPILOT_PROTOXYDE_DECELERATION
            angle *= self.cfg.COPILOT_PROTOXYDE_ANGLE_LOW_COEF
            if self.protoxyde_coeff < self.cfg.COPILOT_PROTOXYDE_THROTTLE_MULT:
                self.protoxyde_coeff = self.cfg.COPILOT_PROTOXYDE_THROTTLE_MULT

        elif abs(mean) < self.cfg.COPILOT_PROTOXYDE_THRESHOLD_LOW:
            # accélération
            self.protoxyde_coeff += self.cfg.COPILOT_PROTOXYDE_ACCELERATION
            if self.protoxyde_coeff > self.cfg.COPILOT_PROTOXYDE_COEFF_MAX:
                self.protoxyde_coeff = self.cfg.COPILOT_PROTOXYDE_COEFF_MAX

        throttle *= self.protoxyde_coeff

        if float(throttle) < self.cfg.COPILOT_PROTOXYDE_THROTTLE_MIN : 
            throttle = self.cfg.COPILOT_PROTOXYDE_THROTTLE_MIN
        if angle > 1: angle = 1
        elif angle < -1: angle = -1

        if self.cfg.COPILOT_PROTOXYDE_DEBUG:
          print("# M: {:<10} A: {:<10} T: {:<10} %: {:<10} || Diff A: {:<10} T: {:<10} ".format(round(mean,4), round(float(self.angle),4), round(float(self.throttle),4), round(float(self.protoxyde_coeff ),4), round(float(self.angle - angle ),4), round(float(throttle - self.throttle ),4)))

        return angle, throttle

    def update(self):
        ColorPrint("Start - copilot_protoxyde")
