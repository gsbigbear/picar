import time, sys
# pip install adafruit-circuitpython-ina219
import adafruit_ina219
import busio

# stdout print color
def ColorPrint(text,color="yellow"): 
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

class copilot_ina219(object):
    def __init__(self,cfg) :
        self.on = True # variable qui sert à indiquer à la fonction update le démarrage de la part
        self.car_frequency = 0
        self.last_calc_time = time.time()
        self.i2c = busio.I2C(3, 2)
        self.ina219 = adafruit_ina219.INA219(self.i2c, 0x42)
        self.cfg = cfg
        self.cfg.toolz_ina219_hz = None
        self.cfg.toolz_ina219_volt = None
        self.cfg.toolz_ina219_mw = None
        self.cfg.toolz_ina219_ma = None
        self.vhistory = []

    def shutdown(self) :  # Cette fonction permet d’arrêter la part lorsque la commande associée est effectuée
        self.on = False
        self.print_volt()
    
    def print_volt(self):
        if self.vhistory != []: 
            ColorPrint("+ Ina219 -------+------VOLT------+") 
            ColorPrint("| Start         |          {:>5} |".format(self.vhistory[0]))
            ColorPrint("| 10%           |          {:>5} |".format(self.vhistory[int(len(self.vhistory)/10)]))
            ColorPrint("| 25%           |          {:>5} |".format(self.vhistory[int(len(self.vhistory)/4)]))
            ColorPrint("| 50%           |          {:>5} |".format(self.vhistory[int(len(self.vhistory)/2)]))
            ColorPrint("| 75%           |          {:>5} |".format(self.vhistory[int(len(self.vhistory)/4)*3]))
            ColorPrint("| End           |          {:>5} |".format(self.vhistory[-1]))
            ColorPrint("+---------------+----------------+")
        else : 
            ColorPrint("+ Ina219 : No history") 

    def update(self) : # Cette fonction s’exécute dès lors où on initialise la part
        ColorPrint("Start - copilot_ina219")
        while self.on : # Tant que la boucle est en cours, les actions ci-dessous s’effectuent
            if self.cfg.COPILOT_HW_INFO :
                self.cfg.toolz_ina219_hz = round(self.car_frequency,4)
                self.cfg.toolz_ina219_volt = round(self.ina219.bus_voltage,4)
                self.cfg.toolz_ina219_mw = round(self.ina219.power,4)
                self.cfg.toolz_ina219_ma = round(self.ina219.current,4)                
                #ColorPrint("INFO : {:>10} Hz | {:>10} V | {:>10} mW | {:>10} mA ".format(self.cfg.toolz_ina219_hz,self.cfg.toolz_ina219_volt, self.cfg.toolz_ina219_mw,self.cfg.toolz_ina219_ma))
                self.vhistory.append(self.cfg.toolz_ina219_volt)
            time.sleep(1) 
    
    def run_threaded(self):
        self.car_frequency = 1/(time.time()-self.last_calc_time)
        self.last_calc_time = time.time()