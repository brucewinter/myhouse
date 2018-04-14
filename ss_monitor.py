#!/usr/bin/python3 -u

# Monitor Survalance Station video/snapshot dir and push results to pushbullet (for info web page update) and autoremote (for phone notification)

# This version filters snapshot photos taken when motion starts.  If the object_detector server sees something interesting, it flags the video for monitoring.

import json
import os
import requests
import stat
import sys
import time
from pushbullet import Pushbullet
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver   # Need to use this one if monitoring a mounted share from another computer, like the NAS

print(time.ctime() + " Starting")

SS_DIR    = '/mnt/surveillance'
PB_KEY    = 'YOUR_PRIVATE_PUSHBULLET_KEY'
PB_ID     = 'YOUR_PUSHBULLET_ID'
AR_KEY    = 'YOUR_PRIVATE_AUTOREMOTE_KEY'
#OG_FILE  = '/home/bruce/mh/local/data/logs/ss_monitor.vlog.txt'
LOG_FILE1 = '/home/bruce/mh/www/ss/ss_monitor.vlog.txt'
LOG_FILE2 = '/home/bruce/mh/www/ss/ss_monitor.slog.txt'
RESTART   = 6   # How many hours between restarts

pb        = Pushbullet(PB_KEY)
nuc       = pb.get_device(PB_ID)

def ar_to_cell (camera):
    r = requests.get("http://autoremotejoaomgcd.appspot.com/sendmessage?key=" + AR_KEY + "&message=motion=:=" + str(camera))
        
class Camera:
    list = {}
    def __init__(self, name):
        self.name = name
        self.file_v   = ''
        self.time_v   = 0
        self.keep     = 0
        self.notified = 0
        self.list[name] = self

def co_by_name(name):
    if name in Camera.list:
        return Camera.list[name]
    else:
        return Camera(name)

        
class file_changed(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):

        if event.is_directory or event.event_type == 'deleted' or event.event_type == 'moved':
            return None
                        
        file = event.src_path

        if "Thumbnail" in file or "laRec" in file:
            return None

        # Sometimes PollingObserver flags old files as new, double check here
        file_age  = time.time() - os.stat(file)[stat.ST_MTIME]
        if file_age > 500:
#           print(" File age > 500, ignoring.  fa=" + str(file_age) + " file=" + file)
            sys.stdout.write('.')
            return None
        
        # Find camera name from filename, eg: /mnt/surveillance/@Snapshot/C4 411s-20180303-1034397423.jpg  or /mnt/surveillance/C2 411/20180227PM/C2 41120180227-125938-1519757978.mp4
        if 'Snapshot' in file:
            fs = file.rsplit('/', 1)
            file_path = fs[0]
            file_name = fs[1]
            fs = file_name.split('-', 1)
            camera  = fs[0]
        else:
            fs = file.rsplit('/', 3)
            file_path = fs[0] + fs[1] + fs[2]
            file_name = fs[3]
            camera    = fs[1]
            
        cameran = camera[1]              # Camera number
        co      = co_by_name(camera)

        if ".jpg" in file:
            if event.event_type == 'created':
                req = "http://localhost:8009?file_dir=" + file_path + "&file=" + file_name
                r = requests.get(req)    # Ask object_server to classify any objects in the snapshot
                rt = r.text
                rj = r.json()
                print(time.ctime() + " snapshot:     camera=" + camera + " f=" + file_name)
                if len(rj) > 0:
                    co.object = rj[0]['name']
                    co.score  = rj[0]['score']
                    print(time.ctime() + " snapshot:     camera=" + camera + " o=" + co.object + " s=" + co.score + " r=" + str(rj))
#                   if True:
                    if "person" in rt or "dog" in rt or "cat" in rt or "wolf" in rt or "car" in rt or "bus" in rt or "cat" in rt or "sheep" in rt or "bird" in rt or "teddy bear" in rt:
                        push = nuc.push_note("Misterhouse", "Camera: snap2 " + co.object + '_' + file_name )   # Send snapshot to info web page monitor
                        co.keep = 1
                        if (co.notified == 0):
#                           ar_to_cell(camera[1] + ' ' + co.object )
                            requests.get("http://192.168.86.150/bin/mh.pl?speak:camera " + camera[1] + " saw a " + co.object )
                            co.notified = 1
                            log_video = open(LOG_FILE2, 'a', 1)
                            log_video.write(co.object + "_" + file_name + "\n")
                            log_video.close()
#                       else:
#                           ar_to_cell("od") # Beep phone for debug for the 1st snapshot of the current sequence
#                   else:
#                       ar_to_cell("no")          # Beep phone for debug
#                       ar_to_cell(camera[1] + ' ' + co.object )



        elif ".mp4" in file:
            if event.event_type == 'created':
                co.file_v = file
                co.time_v = time.time()
#               ar_to_cell("vs")          # Beep phone for debug
                print(time.ctime() + " video start:  camera=" + camera)
            elif event.event_type == 'modified':
                co.time_v = time.time()  # So we can monitor if the file has been fully written
#               print(time.ctime() + " video change: camera=" + camera)
                

def loop1 ():
    startup_time = time.time()
    while True:
        time.sleep(1)
        for camera in Camera.list:
            co = co_by_name(camera)
            if (co.time_v > 0 and ((time.time() - co.time_v) > 5)):    # Time out on video write
                print(time.ctime() + " video done:   camera=" + camera + " v_keep=" + str(co.keep) + " v_file=" + co.file_v)
                if (co.keep == 1):
                    push = nuc.push_note("Misterhouse", "Camera: snapv " + co.file_v )
# Log for a daily review of all triggered videos.  See ~/bin/ss_monitor_review.  Close on each use so we can indepently rotate this file.
                    log_video = open(LOG_FILE1, 'a', 1)
#                   log_video.write("file '" + co.file_v + "'\n")
                    log_video.write(co.file_v + "\n")
                    log_video.close()
                co.time_v   = 0
                co.keep     = 0
                co.notified = 0

# Periodic restart.  PollingObserver flags >1 day old files after a day of nonstop running :(
#       if ((time.time() - startup_time) > 60 * 1):
        if ((time.time() - startup_time) > 3600 * RESTART):
            print(time.ctime() + " Restarting ss_monitor.py\n")
            os.execv(__file__, sys.argv) 
                

class Watcher:
    def __init__(self):
#       self.observer = Observer()            # Use this if SS_DIR is local
        self.observer = PollingObserver()     # Use this if SS_DIR is remote mount

    def run(self):
        event_handler = file_changed()
        self.observer.schedule(event_handler, SS_DIR, recursive=True)
        self.observer.start()
        loop1()


if __name__ == '__main__':
    w = Watcher()
    w.run()

