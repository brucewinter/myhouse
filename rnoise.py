#!/usr/bin/python3 -u

# Calls rec to detect noise.  More info at: https://youtu.be/GcGF6b5X6fI

import os
import sys
import time
from datetime import datetime

inst = sys.argv[1]

card = 'hw:1,0'
if (len(sys.argv) > 2):
    card = sys.argv[2]

def call_rec ():
    print(time.ctime() + " Starting")

    dir1  = '/mnt/nas/temp/noise/rnoise/' 
    tdstamp = datetime.now().strftime("-%m%d-%H%M")

    os.environ['AUDIODRIVER'] = 'alsa'
    os.environ['AUDIODEV']    = card
        

# https://digitalcardboard.com/blog/2009/08/25/the-sox-of-silence/
#   silence [-l] above-periods [duration threshold[d|%] [below-periods duration threshold[d|%]]
#   silence 1 0.5 0.1%   1 0.5 0.1%
#      The first triplet of values means removes silence, if any, at the start until .5 seconds of sound above .1%.
#      The second triplet means stop when there is at least .5 seconds of silence below .1%.

#  In this example, all silence will be trimmed until a noise that is 1% of the sample value is heard for at least 0.1 second, and then trim all silence after 5 seconds of silence is heard below the same 1% threshold.
#   This will result in the noise being recorded to a file called record001.wav. SoX will then start listening for noise again.
#   newfile tells SoX to create multiple output files, and restart tells SoX to repeat the effect chain once more.  The next file recorded will be called record002.wav, followed by record003.wav and so on.
#  Add sinc to create a high pass filter
#  Add trim to create a x second clip, specify a start point (0 seconds) and a duration (5 seconds).
#  rec -c1 -r 192000 record.wav sinc 10k silence 1 0.1 1% trim 0 5

    os.system("/usr/bin/rec -c1 -r   48000 " + dir1 + "/r" + inst + tdstamp + ".wav silence 1 0.3 10% 1 1.0 1% trim 0 1 : newfile : restart ")
#   os.system("/usr/bin/rec -c1 -r   48000 " + dir1 + "/r" + inst + tdstamp + ".wav silence 1 0.3 10% 1 2.0 1% trim 0 2 : newfile : restart ")
#   os.system("/usr/bin/rec -c4 -r   64000 " + dir2 + "/r" + inst + ".wav silence 1 0.3 10% 1 3.0 1% trim 0 3 : newfile : restart 2>&1 /dev/null")
                           
                
call_rec()

    

