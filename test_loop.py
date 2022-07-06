from time import sleep
try:
    import git_python_handler
except:
    pass

for i in range(0,100,5):
    print("i:{}".format(i))
    sleep(1)