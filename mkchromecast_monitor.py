#!/usr/bin/python

# From https://gist.github.com/varazir/13a611976b6e5d4811da83e1150295f5

from __future__ import print_function
import time
import pychromecast
import subprocess

class mediaListener:
    def __init__(self):
        self.oldPlayerStatus = 'NONE'

    def new_media_status(self, status):
        print("mkcc: status=" + status.player_state)
        if (self.oldPlayerStatus != status.player_state):
            self.oldPlayerStatus = status.player_state
            if status.player_state == "PLAYING" or status.player_state == "BUFFERING" or status.player_state == "IDLE":
                print("mkcc: G1 chromecast status is ok")
            else :
                print("mkcc: G1 chromecast staus is bad, restarting mkchromecast")
                subprocess.call("sudo systemctl restart mkchromecast", shell=True)

print("mkcc: Starting mkchromecast_monitor ... ")
#asts = pychromecast.get_chromecast(friendly_name="Living Room")  ... depreciated?  Method is no longer available.
casts = pychromecast.get_chromecasts()
print("mkcc: Looking for G1 ...")
cast = next(cc for cc in casts if cc.device.friendly_name == "G1")
mc = cast.media_controller
#print(cast.device)
#print(mc.status)
#print(mc.status.player_state)

listener = mediaListener()
cast.media_controller.register_status_listener(listener)

listener.new_media_status(mc.status)
print("mkcc: Done with setup, starting loop")
while (1):
    pass

