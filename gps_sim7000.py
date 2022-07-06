"""
sudo screen /dev/ttyUSB2 115200

"""

from time import sleep
try:
    import git_python_handler
except:
    pass

for i in range(0,100,10):
    print("GPS TEST COUNTDOWN: {}".format(i))
    sleep(1)