from time import sleep
try:
    import git_python_handler
except:
    pass
import serial, sys
from time import sleep, time
from micropyGPS import MicropyGPS

NMEA_PORT='/dev/ttyUSB2'
AT_PORT='/dev/ttyUSB2'

def initGNSS():
    sys.stdout.write('Init GNSS\n')
    with serial.Serial(AT_PORT, 115200, timeout=5, rtscts=True, dsrdtr=True) as ser:
        ser.write("AT+CGNSCFG=1\r\n".encode())
        sleep(1)
        ser.write("AT+CGNSPWR=1\r\n".encode())
        sleep(1)

try:
    sys.stdout.write('Started GNSS reader\n')
    reader = MicropyGPS()
    initGNSS()
    while True:
        try:
            with serial.Serial(NMEA_PORT, 115200, timeout=5, rtscts=True, dsrdtr=True) as ser:
                ts = 0
                while True:
                    # update
                    data = ser.read().decode()
                    reader.update(data)
                    # read in every 2 seconds
                    if time() - ts > 2:
                        ts = time()
                        print("UTC_Date={}, UTC_Time={}, lat={}, lng={}".format(reader.date_string(), reader.timestamp, reader.latitude_string(), reader.longitude_string()))

        except Exception as e:
            print("Error Exception: {}".format(str(e)))
            sleep(1)

except KeyboardInterrupt:
    sys.stderr.write('Ctrl-C pressed, exiting GNSS reader\n')