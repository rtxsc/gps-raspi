"""
sudo screen /dev/ttyUSB2 115200
"""

from time import sleep
try:
    import git_python_handler
except:
    pass

# for i in range(0,100,10):
#     print("GPS TEST COUNTDOWN: {}".format(i))
#     sleep(1)

from os import system
import serial
import subprocess
from time import sleep
# from ISStreamer.Streamer import Streamer

# BUCKET_NAME = "movv-project"
# BUCKET_KEY = "SMMSQAMKS9Y9"
# ACCESS_KEY = "ist_PxI02ioOp4KEOeDtd2VfPyWpDdEZ82h6"

SECONDS_BETWEEN_READS   = 5
INIT_DELAY              = 2
READ_COUNT              = 0
STREAM_COUNT            = 0
DATA_POINT              = 2 # GPS lat/lgt recorded before transmission
SERIAL_PORT             = '/dev/ttyUSB2'
SERIAL_BAUD             = 115200

# Start PPPD
def openPPPD():
    # Check if PPPD is already running by looking at syslog output
    print("Opening PPPD...")
    output1 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
    if "secondary DNS address" not in output1 and "locked" not in output1:
        while True:
            # Start the "fona" process
            print("starting fona process...")
            subprocess.call("sudo pon fona", shell=True)
            sleep(2)
            output2 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
#             print(output2)
            if "script failed" not in output2:
                break
#     # Make sure the connection is working
    while True:
        print("Connection check...")
        output2 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
#         output3 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -3", shell=True)
#         print("Out2:{}".format(output2))
#         print("Out3:{}".format(output3))
#         if "secondary DNS address" in output2 or "DNS address" in output3:
        if "secondary DNS address" in output2:
            print("Connection is ready...Device is online...")
            return True

# Stop PPPD
def closePPPD():
    print ("\nTurning off cell connection using sudo poff fona...")
    # Stop the "fona" process
    subprocess.call("sudo poff fona", shell=True)
    # Make sure connection was actually terminated
    while True:
        output = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
        if "Exit" in output:
            print("pppd is now close...")
            return True

# Check for a GPS fix
def checkForFix():
    # print ("checking for fix")
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
                sleep(5)
                ser.write(b"AT+CGNSINF\r")
                print ("Unable to find fix. still looking for fix...")
            else:
                ser.write(b"AT+CGNSINF\r")

# Read the GPS data for Latitude and Longitude
def getCoord():
    # Start the serial connection SIM7000E
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=5, rtscts=True, dsrdtr=True) 
    ser.write(b"AT+CGNSINF\r")
    # print("Getting Latitude/Longitude...")
    while True:
        response = ser.readline().decode()
        if "+CGNSINF: 1," in response:
            # Split the reading by commas and return the parts referencing lat and long
            array = response.split(",")
            lat = array[3]
            # print lat
            lon = array[4]
            # print lon
            return (lat,lon)

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

def main_with_pppd():
    global STREAM_COUNT
    # Initialize the Initial State streamer
    # Start the program by opening the cellular connection and creating a bucket for our data
    if openPPPD():
        # print("\n\n\nOK ALRIGHT THEN! Everything looks good! Starting ISS streamer...")
        # streamer = Streamer(bucket_name=BUCKET_NAME, bucket_key=BUCKET_KEY, access_key=ACCESS_KEY, buffer_size=20)

        # Wait long enough for the request to complete
        for c in range(INIT_DELAY):
            print ("Starting in T-minus {} second".format(INIT_DELAY-c))
            sleep(1)
        while True:
            # Close the cellular connection
            if closePPPD():
                READ_COUNT=0 # reset counter after closing connection
                sleep(1)
            # The range is how many data points we'll collect before streaming
            for i in range(DATA_POINT):
                # Make sure there's a GPS fix
                if checkForFix():
                    # Get lat and long
                    print("i = {}".format(i))
                    if getCoord():
                        READ_COUNT+=1
                        latitude, longitude = getCoord()
                        coord = "lat:" + str(latitude) + "," + "lgt:" + str(longitude)
                        print (coord)
                        # Buffer the coordinates to be streamed
                        print("Saving read #{} into buffer.".format(READ_COUNT))
                        # streamer.log("Coordinates",coord)
                        sleep(SECONDS_BETWEEN_READS) # 1 second
                    # Turn the cellular connection on every 2 reads
                    if i == DATA_POINT-1:
                        sleep(1)
                        print ("opening connection")
                        if openPPPD():
                            STREAM_COUNT+=1
                            # print ("Streaming location to Initial State")
                            # streamer.log("Read Count",str(READ_COUNT))
                            # streamer.log("Stream Count",str(STREAM_COUNT))
                            # # Flush the streaming buffer queue and send the data
                            # streamer.flush() # flush all the 4 readings to ISS
                            # print ("Streaming complete")

def main_without_pppd():
    global READ_COUNT
    # Initialize the Initial State streamer
    # Start the program by opening the cellular connection and creating a bucket for our data
    for c in range(INIT_DELAY):
        print ("Starting in T-minus {} second".format(INIT_DELAY-c))
        sleep(1)
    # streamer = Streamer(bucket_name=BUCKET_NAME, bucket_key=BUCKET_KEY, access_key=ACCESS_KEY, buffer_size=20)
    # Wait long enough for the request to complete
    while True:
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

            payload =   "date:" + str(date_time[0]) + "," + \
                        "time:" + str(time_f)       + "," + \
                        "clat:" + str(clat)  + "," + \
                        "clon:" + str(clon)  + "," + \
                        "spdg:" + str(spdg)  + "," + \
                        "gnsv:" + str(gnsv)  + "," + \
                        "gnsu:" + str(gnsu)  + "," + \
                        "glns:" + str(glns)  

            print (payload)
            print("Saving read #{} into buffer.\n\n".format(READ_COUNT))
            # Buffer the coordinates to be streamed
            # streamer.log("Coordinates",coord)
            sleep(SECONDS_BETWEEN_READS)
            # print "streaming location to Initial State"
            # Flush the streaming queue and send the data
            # streamer.flush()
            # print "streaming complete"

if __name__ == "__main__":
    main_without_pppd()