#!/usr/bin/python3

# More info at: https://youtu.be/GcGF6b5X6fI

# Run on startup with: 
#   /etc/init.d/noise_server.sh
#   sudo service noise_server.sh restart

import json
import os
import re
import shutil
import stat
import time

import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import librosa.display
import numpy as np

from fastai.imports import *
from fastai import *
from fastai.vision import *
from fastai.metrics import error_rate

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver   # Need to use this one if monitoring a mounted share from another computer, like the NAS

from apscheduler.schedulers.background import BackgroundScheduler

dir1  = '/mnt/home/temp/noise/rnoise'

print(time.ctime() + " Starting")

def on_connect(mqttc, obj, flags, rc):
    print("noise connect rc: "+str(rc))
    mqttc.subscribe("noise/+")

def on_publish(mqttc, obj, mid):
    print("noise publish: "+str(mid))

def on_subscribe(mqttc, obj, mid, granted_qos):
    print("noise subscribed: "+str(mid)+" "+str(granted_qos))

def on_log(mqttc, obj, level, string):
    print('noise log: ' + string)

def setup_fastai():
    print('load fastai model')
    path = Path('/mnt/home/temp/noise/empty')
    classes = ['bark', 'cough', 'other', 'sneezeb', 'sneezeh', 'snore', 'throat']
    data = ImageDataBunch.single_from_classes(path, classes, ds_tfms=[], size=224).normalize(imagenet_stats)
    global learn
    learn = cnn_learner(data, models.resnet34)
    learn = learn.load('/mnt/home/temp/noise/models/save_noise_2020_0523b')
    print('model loaded')


def setup_mqtt():
    print('noise mqtt setup')
    global mqttc
    mqttc = mqtt.Client()
#   mqttc.on_message   = on_message
    mqttc.on_connect   = on_connect
#   mqttc.on_publish   = on_publish
#   mqttc.on_log       = on_log
    
    print('noise_server mqtt connect')
    mqttc.username_pw_set(username="my_username",password="my_password")
    mqttc.connect("192.168.0.123")
    mqttc.publish("noise/info", 'noise_server subscribed')

def setup_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.start()
#   scheduler.add_job(reset_dir, 'cron', day='*')


# No need for this, remove files as we use them instead
def reset_dir():
    print(time.ctime() + " Reseting dir: " + dir1);
    shutil.rmtree(dir1)
#   os.rmdir(dir1)
    os.mkdir(dir1)


time_prev = 0
def classify(inst, file):
    file_spec = wav_to_spec(file)
#   print("spec file: " + file_spec)
    img = open_image(file_spec)
    pred_class, pred_idx, outputs = learn.predict(img)
    type = str(pred_class)

    print(time.ctime() + ': Classify type=' + type + ' inst=' + inst + ' file=' + file)
    data = {'inst': inst, 'type': type}
    mqttc.publish('noise/type', json.dumps(data))

# Copy file if it is not right after a previosly copied file (avoid similar back-to-back noises)
    global time_prev
    time_now  = time.time()
    time_diff = time_now - time_prev
#   print('td=' + str(time_diff) + ' tp=' + str(time_prev))
    time_prev = time_now
#   if (time_diff > 15):
    if (time_diff > 30):
        dir = '/mnt/home/temp/noise/latest/' + type
        if not os.path.exists(dir):
            os.mkdir(dir)
#       print('  copy file=' + file + ' dir=' + dir)
# Note: as of ubuntu 12, this fails 'operation not permited' error unless we run as root :(
#
# Skip this until we want to make new models
#       shutil.copy2(file, dir)

    os.remove(file)
    os.remove(file_spec)
            

def wav_to_spec(file_audio):
    file_spec  = file_audio.replace('.wav','.png')
#   print('noise: w_to_s ' + file_audio + '->' + file_spec)
    samples, sample_rate = librosa.load(file_audio)
    fig = plt.figure(figsize=[0.72,0.72])
    ax = fig.add_subplot(111)
    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)
    ax.set_frame_on(False)
    S = librosa.feature.melspectrogram(y=samples, sr=sample_rate)
    librosa.display.specshow(librosa.power_to_db(S, ref=np.max))
    plt.savefig(file_spec, dpi=400, bbox_inches='tight',pad_inches=0)
#   plt.close('all')  # Gives 'Source ID x was not found' error.  Not closeing gives 'More than 209 figures have been opened'
    plt.close() 
    return file_spec

class file_changed(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):
        file = event.src_path

        if event.is_directory or event.event_type == 'deleted' or event.event_type == 'moved':
            return None
        if not '.wav' in file:
            return None
        
        # Sometimes PollingObserver flags old files as new, double check here
        # Not needed, as we now delete files after analizing them.  
#       file_age  = time.time() - os.stat(file)[stat.ST_MTIME]
#       if file_age > 500:
#           print(" File age > 500, ignoring.  fa=" + str(file_age) + " file=" + file)
#           return None


# Note: to avoid grabbing a file still being written to,
#       we detect when the next file is created, then grab the previous file (fs1 - 1 below)

        if event.event_type == 'created':
#           or event.event_type == 'modified':
#           print("New file: " + file)  #  e.g: f = '/mnt/home/temp/noise/rnoise/r2-0108-1329003.wav'
            m = re.search('\/r(\d).+(\d{3})\.wav', file )
            if m:
                inst = m.group(1)
                fs1  = m.group(2)
                fs2 = str(int(fs1) - 1).zfill(3)
                file2 = file.replace(fs1 + '.wav', fs2 + '.wav')
                if os.path.isfile(file2):
                    classify(inst, file2)
                    
# Use this for debug, to playback audio in nr                
#                with open(file_prev, mode='rb') as filein1: # b is important -> binary
#                    fileData = filein1.read()
#                mqttc.publish("noise/filedata", fileData)

class Watcher:
    def __init__(self):
#       self.observer = Observer()            # Use this dir is local
        self.observer = PollingObserver()     # Use this dir is remote mount

    def run(self):
        event_handler = file_changed()
        self.observer.schedule(event_handler, dir1, recursive=False)
        self.observer.start()
        mqttc.loop_forever()

    
if __name__ == '__main__':
    setup_fastai()
    setup_mqtt()
#   setup_scheduler()
    w = Watcher()
    w.run()




                
            
                
