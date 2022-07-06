from git import Repo
import subprocess
import os, sys
import pickle
from time import sleep
from datetime import datetime

COMMITS_TO_PRINT = 1

prev_hexsha = None
current_committed_count = 0
repo_path = '/home/pi/gps-raspi/'

DEFINED_PI_ZERO_W       = False
DEFINED_PI_3B_PLUS      = False
DEFINED_PI_3B           = False
DEFINED_PI_3B_ORI       = False

MAC_PI_3B_ORI           = "b8:27:eb:81:5e:5a" # b8:27:eb:81:5e:5a (eth0) | b8:27:eb:d4:0b:0f (wlan0) 
MAC_PI_3B               = "b8:27:eb:09:ff:57" # eth0
MAC_PI_3B_PLUS          = "b8:27:eb:f0:ad:f0" # eth0
MAC_PI_ZERO_W           = "b8:27:eb:80:a4:3a"

ENABLE_AUDIO            = False # False to make things go faster

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
            if MAC_PI_3B_ORI in get_mac():
                DEFINED_PI_3B_ORI = True
        return model


def load_hexsha_count():
    global prev_hexsha
    global current_committed_count

    if DEFINED_PI_3B_PLUS:
        save_filename = '/home/pi/gps-raspi/saves/pi3bplus_hexsha.pickle'
    if DEFINED_PI_3B:
        save_filename = '/home/pi/gps-raspi/saves/pi3b_hexsha.pickle'
    if DEFINED_PI_3B_ORI:
        save_filename = '/home/pi/gps-raspi/saves/pi3bori_hexsha.pickle'
    if DEFINED_PI_ZERO_W:
        save_filename = '/home/pi/gps-raspi/saves/pizerow_hexsha.pickle'
    try:
        with open(save_filename, 'rb') as f:
            data = pickle.load(f)
            prev_hexsha             = data['hexsha']
            current_committed_count = data['commit_count']
            print("[INFO] Loaded prev hexsha %s and [%d commits] from memory\n" % (prev_hexsha,current_committed_count))
    except:
        current_committed_count = 0
        prev_hexsha = None
        data = { 
            'hexsha'        : prev_hexsha,
            'commit_count'  : current_committed_count
        }
        print("No prev_hexsha file found. Creating new pickle now!")
        with open(save_filename, 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

def save_hexsha_count(new_hexsha,new_commit_count):
    if DEFINED_PI_3B_PLUS:
        save_filename = '/home/pi/gps-raspi/saves/pi3bplus_hexsha.pickle'
    if DEFINED_PI_3B:
        save_filename = '/home/pi/gps-raspi/saves/pi3b_hexsha.pickle'
    if DEFINED_PI_3B_ORI:
        save_filename = '/home/pi/gps-raspi/saves/pi3bori_hexsha.pickle'
    if DEFINED_PI_ZERO_W:
        save_filename = '/home/pi/gps-raspi/saves/pizerow_hexsha.pickle'

    data = { 
        'hexsha'        : new_hexsha,
        'commit_count'  : new_commit_count
    }
    print("\n[INFO] Saving new new_hexsha %s and commit count [%d commits]" % (new_hexsha,new_commit_count))
    with open(save_filename, 'wb') as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

def print_commit_data(commit):
    global prev_hexsha
    global current_committed_count
    print('----- Fetching origin to get the commit hex SHA number -----')
    print(str(commit.hexsha))

def print_repository_info(repo):
    for remote in repo.remotes:
        print('Remote named "{}" with URL "{}"'.format(remote, remote.url))


def playTrack(trackName, blocking = True):
    trackLocation = "/home/pi/gps-raspi/audio/"
    command = "aplay "+ trackLocation + trackName
    if not blocking:
        subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process.communicate()[0]
 
try:
    print("""
                 _ __                    __  __                      __                    ____         
          ____ _(_) /_      ____  __  __/ /_/ /_  ____  ____        / /_  ____ _____  ____/ / /__  _____
         / __ `/ / __/_____/ __ \/ / / / __/ __ \/ __ \/ __ \______/ __ \/ __ `/ __ \/ __  / / _ \/ ___/
        / /_/ / / /_/_____/ /_/ / /_/ / /_/ / / / /_/ / / / /_____/ / / / /_/ / / / / /_/ / /  __/ /    
        \__, /_/\__/     / .___/\__, /\__/_/ /_/\____/_/ /_/     /_/ /_/\__,_/_/ /_/\__,_/_/\___/_/     
       /____/           /_/    /____/                                                                 
    """)
    detect_model() # [CRITICAL] perform once to check for Pi model
    load_hexsha_count()
    repo = Repo(repo_path)
    try:
        if current_committed_count == 0:
            committed_on_pi = False
            repo.remotes.origin.pull() # MUST DO INITIAL PULL FIRST
        else:
            if repo.head.commit.count() > current_committed_count:
                committed_on_pi = True
            else:
                committed_on_pi = False
                repo.remotes.origin.pull() # MUST DO INITIAL PULL FIRST

    except Exception as e:
        print(e)
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y, %H:%M:%S, ")
        if DEFINED_PI_3B_PLUS:
            f = open("/home/pi/gps-raspi/logfile/pi3bplus_githandler_log.txt", "a")
        if DEFINED_PI_3B:
            f = open("/home/pi/gps-raspi/logfile/pi3b_githandler_log.txt", "a")
        if DEFINED_PI_ZERO_W:
            f = open("/home/pi/gps-raspi/logfile/pizerow_githandler_log.txt", "a")
        if DEFINED_PI_3B_ORI:
            f = open("/home/pi/gps-raspi/logfile/pi3bori_githandler_log.txt", "a")
        f.write(str(detect_model() + " " + dt_string + str(e) + "\n"))
        f.close()
        pass

    if not repo.bare:
        # print_repository_info(repo)
        commits = list(repo.iter_commits('origin'))[:COMMITS_TO_PRINT]
        online_committed = len(list(repo.iter_commits('origin')))
        for commit in commits:
            print_commit_data(commit)
            if ( current_committed_count != int(repo.head.commit.count())):
                if not DEFINED_PI_ZERO_W and ENABLE_AUDIO:
                        command = "espeak -ven+f4 -k5 -s175 -a 100 -g3 INFO_Local_commit_number_on_this_device_is_%s" % str(current_committed_count)
                        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        process.communicate()[0]

                if not DEFINED_PI_ZERO_W and ENABLE_AUDIO:
                        command = "espeak -ven+f4 -k5 -s175 -a 100 -g3 INFO_Latest_commit_number_on_GitHub_is_%s" % str(repo.head.commit.count())
                        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        process.communicate()[0]

                if committed_on_pi:
                    diff = current_committed_count - repo.head.commit.count()
                    print("diff = current_committed_count [%d] - repo head [%d]" % (current_committed_count,repo.head.commit.count()))
                else:
                    diff = repo.head.commit.count() - current_committed_count
                    print("diff = repo head [%d] - current_committed_count [%d]" %(repo.head.commit.count(), current_committed_count))
                if diff > 0:
                    print('[INFO] Your local commit is {} commits behind origin.\n'.format(diff))
                    if not DEFINED_PI_ZERO_W and ENABLE_AUDIO:
                        command = "espeak -ven+f4 -k5 -s125 -a 100 -g10 Your_local_commit_is_%s_commits_behind_origin" % str(diff)
                        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        process.communicate()[0]
                        playTrack("local-behind-origin.wav")
                        playTrack("pull-repo.wav")
                    print('[INFO] Pulling commit {} from origin'.format(repo.head.commit.count()))
                    repo.remotes.origin.pull()
                    save_hexsha_count(str(repo.head.commit.hexsha), int(commit.count()))
                    if not DEFINED_PI_ZERO_W and ENABLE_AUDIO:
                        playTrack("local-repo-updated.wav")
                    os.execv(sys.executable, ['python3'] + sys.argv) 
                elif diff < 0:
                    if not DEFINED_PI_ZERO_W and ENABLE_AUDIO:
                        playTrack("local-ahead-origin.wav")
                    print('[INFO] Your local commit is {} commits ahead previous saved origin.\n'.format(abs(diff)))
                    # repo.remotes.origin.push()
                    print('[INFO] Pulling commit no matter what')
                    repo.remotes.origin.pull()
                    save_hexsha_count(str(repo.head.commit.hexsha), int(commit.count()))
                else:
                    print('[INFO] You are up-to-date with remote repo.')

            else:
                print("""
                   __  __            __                  __      __     
                  / / / /___        / /_____        ____/ /___ _/ /____ 
                 / / / / __ \______/ __/ __ \______/ __  / __ `/ __/ _ \\
                / /_/ / /_/ /_____/ /_/ /_/ /_____/ /_/ / /_/ / /_/  __/
                \____/ .___/      \__/\____/      \__,_/\__,_/\__/\___/ 
                    /_/  
                                                                            
                """)
                print("\n[INFO] Nothing Fetched. Local repo already up-to-date with commit [%d]." % int(commit.count()))
                if not DEFINED_PI_ZERO_W and ENABLE_AUDIO:
                    playTrack("git-pull-not-required.wav")
                    pass
    else:
        print('Could not load repository at {} :'.format(repo_path))

except KeyboardInterrupt:
    print("Bye-bye ! Keyboard Interrupt Detected")
