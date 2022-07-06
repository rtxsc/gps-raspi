#!/usr/bin/env python3
try:
    import git_python_handler
except:
    pass
import psutil
import board
from digitalio import DigitalInOut, Direction, Pull
import adafruit_ssd1306
import busio as io
import shlex, subprocess
import os, sys
from time import sleep
import datetime
import time
import pickle
from git import Repo
import serial


DEFINED_PI_ZERO_W       = False
DEFINED_PI_3B_PLUS      = False
DEFINED_PI_3B           = False
DEFINED_PI_3B_ORI       = False

MAC_PI_3B_ORI           = "b8:27:eb:81:5e:5a"
MAC_PI_3B               = "b8:27:eb:09:ff:57"
MAC_PI_3B_PLUS          = "b8:27:eb:f0:ad:f0"
MAC_PI_ZERO_W           = "b8:27:eb:80:a4:3a"
FW_VERSION              = "None"

previous_ssid = None
conn_started_ts = 0
disconn_started_ts = 0
disconnected = False

SECONDS_BETWEEN_READS   = 1
INIT_DELAY              = 2
READ_COUNT              = 0
STREAM_COUNT            = 0
DATA_POINT              = 2 # GPS lat/lgt recorded before transmission
SERIAL_PORT             = '/dev/ttyUSB2'
SERIAL_BAUD             = 115200

try:
    import machine
    gettime = lambda: time.ticks_ms()
except ImportError:
    const = lambda x: x
    gettime = lambda: int(time.time() * 1000) 

def checkForFix():
    print ("checking for fix")
    # Start the serial connection SIM7000E - ttyUSB2 on Pi Zero W
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=5, rtscts=True, dsrdtr=True) 
    # Turn on the GPS
    ser.write(b"AT+CGNSPWR=1\r")
    ser.write(b"AT+CGNSPWR?\r")
    while True:
        response = ser.readline()
        if b"1" in response: # remove the whitespace before 1 for SIM7000E
            # print("GPS is ON!")
            break
    # Ask for the navigation info parsed from NMEA sentences
    ser.write(b"AT+CGNSINF\r")
    print("Getting NMEA information from Satellite...")
    while True:
        response = ser.readline()
        # Check if a fix was found
        if b"+CGNSINF: 1,1," in response:
            # print ("Fix found! OK!")
            # print response
            return True
        # If a fix wasn't found, wait and try again
        if b"+CGNSINF: 1,0," in response:
            sleep(1)
            ser.write(b"AT+CGNSINF\r")
            print ("Unable to find fix. still looking for fix...")
            return False
        else:
            ser.write(b"AT+CGNSINF\r")

def getCGNSINF():
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=5, rtscts=True, dsrdtr=True) 
    ser.write(b"AT+CGNSINF\r")
    # print("Getting Speed/Satellite Count...")
    while True:
        response = ser.readline().decode()
        if "+CGNSINF: 1," in response:
            array = response.split(",")
            grun = array[0] # GNSS run status
            sfix = array[1] # Fix status
            utct = array[2] # UTC date & time
            clat = array[3] # latitude
            clon = array[4] # longitude
            altd = array[5] # MSL altitude
            spdg = array[6] # speed over ground
            csog = array[7] # course over ground
            mfix = array[8] # fix mode
            rsv1 = array[9] # reserved1
            hdop = array[10] # HDOP horizontal dilution of precision
            pdop = array[11] # PDOP position (3D) dilution of precision
            vdop = array[12] # VDOP vertical dilution of precision
            rsv2 = array[13] # reserved2
            gnsv = array[14] # GNSS Satellites in View
            gnsu = array[15] # GNSS Satellites in Use
            glns = array[16] # GLONASS Satellites Used
            rsv3 = array[17] # reserved3
            cnom = array[18] # C/N0 max
            hpa0 = array[19] # Horizontal Position Accuracy
            vpa0 = array[20] # Vertical Position Accuracy

            # print("MSL altitude:{}m = {}ft".format(altd,round(float(altd)/0.3048),4))
            # print("Speed over Ground:{} km/h".format(spdg))
            # print("Course over Ground:{} degrees".format(csog))
            # print("HDOP:{}".format(hdop))
            # print("PDOP:{}".format(pdop))
            # print("VDOP:{}".format(vdop))
            # print("C/N0 max:{} dBHz".format(cnom))
            # print("HPA:{} m".format(hpa0))
            # print("VPA:{} m".format(vpa0))
            # print("GNSS Satellites in View:{}".format(gnsv))
            # print("GNSS Satellites in Use:{}".format(gnsu))
            # print("GLONASS in Use:{}".format(glns))
            return utct, clat, clon, spdg, gnsv, gnsu, glns
        else:
            print('Waiting for response')
        sleep(0.5)

def main_without_pppd():
    global READ_COUNT
    # Make sure there's a GPS fix before proceeding to data acquisition
    if checkForFix():
        READ_COUNT+=1
        utct, clat, clon, spdg, gnsv, gnsu, glns = getCGNSINF() # 6.7.2022 Wednesday
        
        utct_float  = float(utct)
        utct_int    = int(utct_float)
        utct_string = str(utct_int)

        date_time   = []
        time_array  = []
        datelength  = 8
        timelength  = 2
        for i in range(0, len(utct_string), datelength):
            date_time.append(utct_string[i : i+datelength])

        time_int = int(date_time[1]) + 80000 

        time_str = str(time_int)
        for index in range(0, len(time_str), timelength):
            time_array.append(time_str[index : index+timelength])
        
        time_f = time_array[0] + ':' + time_array[1] + ':' + time_array[2]
        # print("Date:{}".format(date_time[0]))
        # print("Time:{}".format(time_f))

        payload =   "date:" + str(date_time[0]) + ", " + \
                    "time:" + str(time_f)       + ", " + \
                    "clat:" + str(clat)  + ", " + \
                    "clon:" + str(clon)  + ", " + \
                    "spdg:" + str(spdg)  + ", " + \
                    "gnsv:" + str(gnsv)  + ", " + \
                    "gnsu:" + str(gnsu)  + ", " + \
                    "glns:" + str(glns)  

        print (payload)
        print("Saving read #{} into buffer.\n\n".format(READ_COUNT))
        sleep(SECONDS_BETWEEN_READS) # disabled cuz we use OLED loop delay
        return date_time[0],time_f,clat, clon, spdg, gnsv, gnsu, glns
    else:
        print("Unable to find fix. Trying again later in the next loop around")

def load_hexsha_count() -> str:
    repo_path = '/home/pi/gps-raspi/'
    repo = Repo(repo_path)
    commit_count = repo.head.commit.count()
    headcommit = repo.head.commit
    _committed_date = headcommit.committed_date + 28800
    s = time.asctime(time.gmtime(_committed_date))
    # _committed_date = time.strftime("%a, %d %b %Y %H:%M", time.gmtime(_committed_date))
    return str(commit_count), s

def get_mac():
    from getmac import get_mac_address
    eth_mac = get_mac_address(interface="eth0")
    return eth_mac

def detect_model() -> str:
    global DEFINED_PI_ZERO_W
    global DEFINED_PI_3B
    global DEFINED_PI_3B_PLUS
    global DEFINED_PI_3B_ORI
    with open('/proc/device-tree/model') as f:
        model = f.read()
        if "Raspberry Pi Zero W" in model:
            if MAC_PI_ZERO_W in get_mac():
                DEFINED_PI_ZERO_W = True
        elif "Raspberry Pi 3 Model B Plus Rev 1.3" in model:
            if MAC_PI_3B_PLUS in get_mac():
                DEFINED_PI_3B_PLUS = True
        elif "Raspberry Pi 3 Model B Rev 1.2" in model:
            if MAC_PI_3B in get_mac():
                DEFINED_PI_3B = True
            else:
                DEFINED_PI_3B_ORI = True
        else:
            model = "unidentified board"

        return model

detect_model() # [CRITICAL] perform once to check for Pi model

def load_fw_version():
    global FW_VERSION

    if DEFINED_PI_3B_PLUS:
        save_filename = '/home/pi/gps-raspi/saves/pi3bplus_fw.pickle'
    if DEFINED_PI_ZERO_W:
        save_filename = '/home/pi/gps-raspi/saves/pizerow_fw.pickle'
    if DEFINED_PI_3B:
        save_filename = '/home/pi/gps-raspi/saves/pi3bopencv_fw.pickle'
    if DEFINED_PI_3B_ORI:
        save_filename = '/home/pi/gps-raspi/saves/pi3bori_fw.pickle'
    
    try:
        with open(save_filename, 'rb') as f:
            data = pickle.load(f)
            FW_VERSION = data['fw_version']
            print("Loaded FW_Ver %s  from memory " %  FW_VERSION)
    except:
        data = { 
            'fw_version'  : FW_VERSION
        }
        print("No FW_Ver file found. Creating new pickle now!")
        with open(save_filename, 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

if DEFINED_PI_ZERO_W:
    restart_pin = DigitalInOut(board.D16) # for Pi Zero W
    shut_down_pin = DigitalInOut(board.D20) # for Pi Zero W
else:
    restart_pin = DigitalInOut(board.D23) # for Pi 3B Plus / 3B standard
    shut_down_pin = DigitalInOut(board.D27) # for Pi 3B Plus / 3B standard

restart_pin.direction = Direction.INPUT
shut_down_pin.direction = Direction.INPUT
# modified on 3.11.2021 referred via https://www.npmjs.com/package/onoff
# https://github.com/fivdi/onoff/wiki/Enabling-Pullup-and-Pulldown-Resistors-on-The-Raspberry-Pi

shut_down_pin.pull = Pull.UP # good to know this method anyway
restart_pin.pull = Pull.UP

buzz = DigitalInOut(board.D26)
buzz.direction = Direction.OUTPUT

# LED for testing SSID acquisition operation within Python
test_led = DigitalInOut(board.D18)
test_led.direction = Direction.OUTPUT
test_led.value      = 0

i2cErrorSignal = DigitalInOut(board.D21)
i2cErrorSignal.direction = Direction.OUTPUT

pytonProcess = subprocess.check_output("ps aux | grep main",shell=True).decode()
pytonProcess = pytonProcess.split('\n')
  
for process in pytonProcess:
    print(process)

process_name = "python3"
pid = None

for proc in psutil.process_iter():
    if process_name in proc.name():
       pid = proc.pid
       name = proc.name
       print(pid, name)

process = psutil.Process(pid)
process_name = process.name()
print("Process: %s , Name: %s" %(process.pid,process_name))

def get_uptime():
    cmd = "uptime -p"
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    if p is not None:
        output = p.communicate()[0]
        return output.decode('utf-8')

def beep_twice():
    buzz.value = True
    sleep(0.5)
    buzz.value = False
    sleep(0.1)
    buzz.value = True
    sleep(0.5)
    buzz.value = False

try:
    load_fw_version()
    print("[IMPORTANT INFO] Please ensure that font5x8.bin file is available at /home/pi/")
    i2c = io.I2C(board.SCL, board.SDA)
    # once i2c succesfully initialized, then proceed with i2c object declaration
    oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

except (OSError,ValueError,NameError):
    # print("Oops!", sys.exc_info()[0], "occurred.")
    beep_twice()
    for i in range(0,5):
        if(i%2==0):
            i2cErrorSignal.value = True
        else:
            i2cErrorSignal.value = False
        sleep(0.1)


# modular function to shutdown Pi
def shut_down():
    if DEFINED_PI_ZERO_W:
        print("[WARNING] Shutting down Pi now from button D20 press!")
    else:
        print("[WARNING] Shutting down Pi now from button D27 press!")
    command = "/usr/bin/sudo /sbin/shutdown -h now"
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print(output)

def restart():
    if DEFINED_PI_ZERO_W:
        print("Restarting Pi via D16 interrupt")
    else:
        print("Restarting Pi via D23 interrupt")
    command = "/usr/bin/sudo /sbin/reboot -h now"
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print(output)

def get_ip_ssid():
    global local_ip
    global ssid_str
    global previous_ssid
    global conn_started_ts
    global disconn_started_ts
    global disconnected
    test_led.value = 1 # turn on led D18 to signal searching for ssid name
    # print("checking for IP address and connected SSID")
    device = 'wlan0'
    """
    ip addr show wlan0 | awk '$1 == "inet" {gsub(/\/.*$/,"",$2); print $2}'
    """
    cmd = "ip addr show %s | awk '$1 == \"inet\" {gsub(/\/.*$/, \"\", $2); print $2}'" % device
    try:
        p = subprocess.Popen(cmd, shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)

        out, _ = p.communicate()
        local_ip = str(out.strip().decode('UTF-8'))
        output = subprocess.check_output(['iwgetid'])
        out = output.split(b'"')[1]
        ssid_str = out.decode('UTF-8')
        disconnected = False
        test_led.value = 0 # turn off led D18 after successfully obtaining ssid
    except:
        if not disconnected:
            disconn_started_ts = gettime()
            disconnected = True
            oled.fill(0)
            oled.text('Disconnected SSID', 0, 0, True)
            oled.text('Scanning for network', 0, 10, True)
            oled.text('Logic 28 FEB 2022', 0, 20, True)
            oled.show()

    if ssid_str != previous_ssid:
        conn_started_ts = gettime()
        previous_ssid = ssid_str

buzz.value = True
sleep(0.05)
buzz.value = False
sleep(0.1)

buzz.value = True
sleep(0.05)
buzz.value = False
sleep(0.1)


try:
    while True:
        get_ip_ssid()
        commit_number, committed_date = load_hexsha_count()
        model_name = detect_model()
        conn_elapse = int((gettime() - conn_started_ts)/1000)
        conn_elapse_pretty =  str(datetime.timedelta(seconds = conn_elapse)) # timedelta require direct import datetime
        # print("conn elapse pretty: {}".format(conn_elapse_pretty.split(".")[0]))
        # print("SSID {} connected time:{}s".format(previous_ssid,conn_elapse))
        for i in range (0,127,2):
            if not disconnected:
                oled.fill(0)
                if i < 25:
                    oled.text('Conn:'+str(conn_elapse_pretty)+'s', 0, 0, True)
                    oled.text('>>'+ssid_str+'<<', 0, 10, True)
                    oled.text('>>FW_Ver:'+FW_VERSION+'<<', 0, 20, True)
                elif i >= 25 and i < 50:
                    oled.text('>>>>>>> MODEL <<<<<<<', 0, 0, True)
                    oled.text(model_name[0:21], 0, 10, True)
                    oled.text(model_name[21:42], 0, 20, True)
                elif i >= 50 and i < 75:
                    oled.text('>>> COMMIT NUMBER <<<', 0, 0, True)
                    oled.text(committed_date, 0, 10, True)
                    oled.text("Commit #" + commit_number, 0, 20, True)
                elif i >= 75 and i < 100:
                    try:
                        date_time,time_f,clat, clon, spdg, gnsv, gnsu, glns = main_without_pppd()
                    except TypeError:
                        print("TypeError avoided due to GPS not able to find fix")
                        date_time = "None"
                        time_f = "None"
                        clat = "0.00"
                        clon = "0.00"
                        spdg = "None"
                        gnsv = 'N'
                        gnsu = 'N'
                        glns = 'N'
                        sleep(1)
                        pass
                    oled.text('GPS_T:'+time_f, 0, 0, True)
                    oled.text(clat+','+clon, 0, 10, True)
                    oled.text('GNSV:'+gnsv+' U:'+gnsu+' GLNS:'+glns, 0, 20, True)
                else:
                    # if not DEFINED_PI_ZERO_W:
                    #     oled.text('PRESS D23 to RESTART', 0, 0, True)
                    # else:
                    #     oled.text('PRESS D16 to RESTART', 0, 0, True)
                    if not DEFINED_PI_ZERO_W:
                        oled.text('PRESS D27 to SHUTDOWN', 0, 0, True)
                    else:
                        oled.text('PRESS D20 to SHUTDOWN', 0, 0, True)

                    oled.text(get_uptime(), 0, 10, True)
                    oled.text('>>'+local_ip+'<<', 0, 20, True)
                for j in range (0,int(i/2)):
                    oled.text('>',j, 29, True)
                for k in range (127-int(i/2),127):
                    oled.text('<',k, 29, True)
                oled.show()
            else:
                disconn_elapse = int((gettime() - disconn_started_ts)/1000)
                disconn_elapse_pretty =  str(datetime.timedelta(seconds = disconn_elapse)) # timedelta require direct import datetime
                oled.fill(0)
                oled.text('Disconnected SSID', 0, 0, True)
                oled.text(get_uptime(), 0, 10, True)
                oled.text('Down elapse:'+str(disconn_elapse_pretty), 0, 20, True)
                for j in range (0,int(i/2)):
                    oled.text('>',j, 29, True)
                for k in range (127-int(i/2),127):
                    oled.text('<',k, 29, True)
                oled.show()

            pinState = shut_down_pin.value
            pinRestart = restart_pin.value
            # print(pinState, pinRestart)
            if(pinRestart == False):
                oled.fill(0)
                beep_twice()
                sleep(0.5)
                beep_twice()
                oled.text('RESTARTING PI NOW',0,0,True)
                oled.text('D26 Interrupt Detected',0,10,True)
                oled.text('sudo reboot now',0,20,True)
                oled.show()
                sleep(2)
                restart()

            if(pinState == False):
                beep_twice()
                oled.fill(0)
                oled.text('SHUTTING DOWN NOW', 0, 0, True)
                oled.text('Bye-bye from Pi', 0, 10, True)
                oled.text('See You Soon', 0, 20, True)
                oled.show()
                sleep(2)
                shut_down()
        sleep(1)

except KeyboardInterrupt:
    print("Program Halted by Ctrl+C")

except Exception as e:
    e = str(e)
    print("Exception Caught: %s\n" %  e)
    now = datetime.datetime.now()
    dt_string = now.strftime("%d/%m/%Y, %H:%M:%S, ")
    if DEFINED_PI_3B_PLUS:
        f = open("/home/pi/gps-raspi/logfile/pi3bplus_safe_shutdown_log.txt", "a")
    if DEFINED_PI_3B:
        f = open("/home/pi/gps-raspi/logfile/pi3b_safe_shutdown_log.txt", "a")
    if DEFINED_PI_ZERO_W:
        f = open("/home/pi/gps-raspi/logfile/pizerow_safe_shutdown_log.txt", "a")
    if DEFINED_PI_3B_ORI:
        f = open("/home/pi/gps-raspi/logfile/pi3bori_safe_shutdown_log.txt", "a")
    f.write(str(detect_model() + " " + dt_string + e + "\n"))
    f.close()
    os.execv(sys.executable, ['python3'] + sys.argv) 
