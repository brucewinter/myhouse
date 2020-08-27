# -*- coding: utf-8 -*-

# Monitor air quality, graph it to a local LCD, send it to a smarthouse via mqtt,
# and control a range hood fan for smoke control using switchbots

# More info at:
#   https://youtu.be/UTyxMI9BEzo
#   https://github.com/brucewinter/myhouse/blob/master/air.py

# Other videos at:
#   https://www.youtube.com/brucewinter

# Note:
#  Local fan control via switchbot is done from the smart house program via mqtt, for more sophisticated control (e.g. hysteresis)
#  Simple control could be done directly without a smart house. 

import os, time, math, subprocess, digitalio, board, json, busio, adafruit_pm25
import adafruit_rgb_display.st7789 as st7789
import paho.mqtt.client as mqtt
from   adafruit_rgb_display.rgb import color565
from   PIL import Image, ImageDraw, ImageFont

air_data = {}
air_data_file = 'air_data.json'

# Get previous air data for plots
def load_data():
    global air_data
    print('Loading previous air history')
    if os.path.isfile(air_data_file):
        f = open(air_data_file)
        try: air_data = json.load(f)
        except: print('Unable to load jason data')

    if 'g1' not in air_data: air_data['g1'] = {'p003' : [],    'pm010s' : []}      # 40 min chart
    if 'g2' not in air_data: air_data['g2'] = {'p003' : [],    'pm010s' : []}      # 4 hour chart
    if 'g3' not in air_data: air_data['g3'] = {'p003' : [0],   'pm010s' : [0]}     # max chart
    if 'g4' not in air_data: air_data['g4'] = {'p003' : [999], 'pm010s' : [999]}   # min chart
#   print(air_data)
        
def setup_mqtt():
    global mqttc
    print('air mqtt setup')
    mqttc = mqtt.Client()
    mqttc.on_connect   = on_connect
    mqttc.on_message   = on_message
#   mqttc.on_log       = on_log       # Use this for debugging errors in callbacks
    mqttc.username_pw_set(username='secret_name',password='secret_password')
    mqttc.connect('192.168.86.111')

def on_connect(mqttc, obj, flags, rc):
    print('air connect rc: '+str(rc))
    mqttc.subscribe('ha/heartbeat')
    mqttc.subscribe('sensor/+')
    mqttc.subscribe('ha/stove')

data = {'td' : ' '}
def on_message(mqttc, obj, msg):
    p = msg.payload.decode('utf-8')
#   print('air message: ' + str(msg.topic) + ' = ' + p)
    if msg.topic == 'ha/heartbeat' :  data['td'] = time.strftime('%a %d %I:%M:%S', time.localtime(int(p) / 1000))
    if msg.topic == 'sensor/Outside Temperature' :  data['tout'] = p
    if msg.topic == 'sensor/Upstairs Temperature' : data['tin'] = p
    if msg.topic == 'ha/stove' :  os.system('/mnt/nas/bin/switchbot_stove ' + p)
    if msg.topic == 'ha/stove' :  os.system('/mnt/nas/bin/switchbot_stove ' + p)
    
def on_log(mqttc, obj, level, string):
    print(string)

def setup_pm25():
    global pm25
    reset_pin = None
    i2c = busio.I2C(board.SCL, board.SDA, frequency=100000) # Create library object, use 'slow' 100KHz frequency!
    pm25 = adafruit_pm25.PM25_I2C(i2c, reset_pin)  # Connect to a PM2.5 sensor over I2C
    print('Found PM2.5 sensor, reading data...')

def setup_display():
    global my_disp, draw, font, fontsize, image, rotation, height, width, top, bottom, backlight, buttonA, buttonB

    # Configuration for CS and DC pins (these are FeatherWing defaults on M0/M4):
    cs_pin = digitalio.DigitalInOut(board.CE0)
    dc_pin = digitalio.DigitalInOut(board.D25)
    reset_pin = None

    BAUDRATE = 64000000     # Config for display baudrate (default max is 24mhz):

    spi = board.SPI()     # Setup SPI bus using hardware SPI:

    my_disp = st7789.ST7789(
        spi,
        cs=cs_pin,
        dc=dc_pin,
        rst=reset_pin,
        baudrate=BAUDRATE,
        width=240,
        height=240,
        x_offset=0,
        y_offset=80,
    )

    # Create blank image for drawing.  Make sure to create image with mode 'RGB' for full color.
    height = my_disp.width  # we swap height/width to rotate it to landscape!
    width  = my_disp.height
    image  = Image.new('RGB', (width, height))
    rotation = 180
    padding = -2
    top = padding
    bottom = height - padding

    draw = ImageDraw.Draw(image)     # Get drawing object to draw on image.

    # Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
    fontsize   = font.getsize('hi')[1]

    # Turn on the backlight
    backlight = digitalio.DigitalInOut(board.D22)
    backlight.switch_to_output()
    backlight.value = True

    # Setup up buttons
    buttonA = digitalio.DigitalInOut(board.D23)
    buttonB = digitalio.DigitalInOut(board.D24)
    buttonA.switch_to_input()
    buttonB.switch_to_input()

def get_cpu_data():
#   print('1', end='', flush=True)

#   cmd = "hostname -I | cut -d' ' -f1"
#   data['ip'] = 'IP: ' + subprocess.check_output(cmd, shell=True).decode('utf-8')
#   cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
#   data['mem'] = subprocess.check_output(cmd, shell=True).decode("utf-8")
#   cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\''
#   data['disk'] = subprocess.check_output(cmd, shell=True).decode("utf-8")

#   cmd = "top -bn1 | grep load | awk '{printf \"%.2f\", $(NF-2)}'"
    cmd = "cat /proc/loadavg | cut -d' ' -f1"
    data['cload'] = subprocess.check_output(cmd, shell=True).decode("utf-8").rstrip()

    cmd = "cat /sys/class/thermal/thermal_zone0/temp |  awk '{printf \"%i\", $(NF-0) / 1000}'"  # pylint: disable=line-too-long
    data['ctemp'] = subprocess.check_output(cmd, shell=True).decode("utf-8")

    cmd = "uptime | cut -d',' -f1 | cut -d' ' -f4,5"
    data['uptime'] = subprocess.check_output(cmd, shell=True).decode("utf-8")


def get_air_data():
    global air_data
    try:
        pm25_data = pm25.read()
        # print(pm25_data)
    except RuntimeError:
        print('Unable to read from sensor, retrying...')
        return

    print('*', end='', flush=True)

    pm010s = pm25_data['pm10 standard']
    pm020s = pm25_data['pm25 standard']
    pm100s = pm25_data['pm100 standard']
    pm010e = pm25_data['pm10 env']
    pm020e = pm25_data['pm25 env']
    pm100e = pm25_data['pm100 env']
    p003   = pm25_data['particles 03um']
    p005   = pm25_data['particles 05um']
    p010   = pm25_data['particles 10um']
    p025   = pm25_data['particles 25um']
    p050   = pm25_data['particles 50um']
    p100   = pm25_data['particles 100um']
    
    data['rpms'] = 'S: ' + str(pm010s) + ' ' + str(pm020s) + ' ' + str(pm100s)
    data['rpme'] = 'E: ' + str(pm010e) + ' ' + str(pm020e) + ' ' + str(pm100e)
    data['rp1']  = 'P: ' + str(p003)   + ' ' + str(p005)   + ' ' + str(p010) 
    data['rp2']  = 'P: ' + str(p025)   + ' ' + str(p050)   + ' ' + str(p100)

    p003  = int(p003) # Is always > 10, so need for floating point
    p003l = int(10 * math.log10(p003)) if p003 > 0 else 0
    pm010sl = 220 if pm010s > 220 else pm010s

    t = int(time.time())

    if t % 5 == 0 :
        mqttc.publish('sensor/air 1', json.dumps(pm25_data))

    # Data for a 40 min graph.  240 / 40 =  6 readings per minute, 1 every 10 seconds.
    if t % 10 == 0 :
        air_data['g1']['p003'].append(p003l)
        air_data['g1']['pm010s'].append(pm010sl)
        if len(air_data['g1']['pm010s']) > 240:
            air_data['g1']['p003']   = air_data['g1']['p003'][1:]
            air_data['g1']['pm010s'] = air_data['g1']['pm010s'][1:]

    # Data for a 4 hour graph.  240 / 4*60 = 1 readings per minute
    if t % 60 == 0 :
        air_data['g2']['p003'].append(p003l)
        air_data['g2']['pm010s'].append(pm010sl)
        if len(air_data['g2']['pm010s']) > 240:
            air_data['g2']['p003']   = air_data['g2']['p003'][1:]
            air_data['g2']['pm010s'] = air_data['g2']['pm010s'][1:]

    if p003   < air_data['g4']['p003'][-1]   :  air_data['g4']['p003'][-1]   = p003
    if pm010s > air_data['g3']['pm010s'][-1] :  air_data['g3']['pm010s'][-1] = pm010s

    # Data for a 2 day graph.  240 / 48   hours = 5     per hour, 1 for every 12 minutes
    # Data for a 4 day graph.  240 / 96   hours = 2.5   per hour, 1 for every 24 minutes
    # Data for a 7 day graph.  240 / 7*24 hours = 1.429 per hour, 1 for every 42 minutes
    if t % (60*24) == 0 :
        print('24 minute data')
        air_data['g4']['p003'].append(999)
        air_data['g3']['pm010s'].append(0)
        if len(air_data['g4']['p003']) > 240:
            air_data['g4']['p003'] = air_data['g4']['p003'][1:]
        if len(air_data['g3']['pm010s']) > 240:
            air_data['g3']['pm010s']  = air_data['g3']['pm010s'][1:]

    if t % (60*10) == 0 :
        print('Saving air_data')
        with open(air_data_file, 'w') as f:
            json.dump(air_data, f, sort_keys=True, indent=4)
        f.close()

        
def display_data():
    draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))     # Clear screen

    if not buttonA.value :
        display_data2()
    elif not buttonB.value :
        display_data3()
    else :
        display_data1()
        
    my_disp.image(image, rotation)     # Display image.

    
def display_data1():
    global air_data

    plot_data(air_data['g1']['p003'],    2, '#FF0000')  # red   40 minute chart
    plot_data(air_data['g1']['pm010s'], .5, '#00FF00')  # green 40 minute chart

    to = data.get('tout', 0)
    ti = data.get('tin', 0)
    temps = 'Out: ' + str(to) + ' In:' + str(ti)
    temps_diff = float(to) - float(ti)
    if abs(temps_diff) < 1 :
        temps_color = '#00FF00'
    elif temps_diff > 0 :
        temps_color = '#FF0000'
    else :
        temps_color = '#0000FF'
        
    cpu = 'C: ' + data['cload'] + ' ' + data['ctemp'] + ' ' + data['uptime']
    
    x = 0
    y = top

    draw.text((x, y), data['td'], font=font, fill='#FFFFFF')
    y += fontsize
    draw.text((x, y), temps, font=font, fill = temps_color)
    y += fontsize
    draw.text((x, y), data['rpms'], font=font, fill='#FFFFFF')
    y += fontsize
    draw.text((x, y), data['rp1'], font=font, fill='#FFFFFF')
    y += fontsize
    draw.text((x, y), data['rp2'], font=font, fill='#FFFFFF')
    y += fontsize
    draw.text((x, y), cpu, font=font, fill='#0000FF')
    y += fontsize
   
def display_data2():
    global air_data
    plot_data(air_data['g2']['p003'],   2, '#FF0000')  # red   4 hour chart
    plot_data(air_data['g2']['pm010s'], 1, '#00FF00')  # green 4 hour chart

def display_data3():
    global air_data
    plot_data(air_data['g3']['pm010s'], 0.5, '#00FF00') # 4 day max chart
    plot_data(air_data['g4']['p003'],   0.2, '#0000FF') # 4 day min chart.  Scale so average min, 150 ish, is about 30.

def plot_data(data, scale, color):
    x = 0
    for i in data:
        x = x + 1
        y = bottom - int(scale * i)
        draw.line((x, bottom, x, y), width=1, fill=(color))
        if x % 60 == 0 :   # Draw 4 grid lines
            draw.line((x, bottom, x, 150), width=1, fill=('#FFFFFF'))

def myloop():
    while True:
        t = time.time()
        print(time.strftime('%a %d %I:%M:%S', time.localtime()), end=' ', flush=True)
        print('.', end='', flush=True)
        get_air_data()
        print('-', end='', flush=True)
        get_cpu_data()
        print('+', end='', flush=True)
        display_data()
        print('=',         flush=True)
        # Sleep enough to give 1 loop per second.  Skip if this was a slow pass for whatever reason
        ts = 1 - (time.time() - t)
        print(ts)
        if ts > 0: time.sleep(ts)
        
if __name__ == '__main__':
    load_data()
    setup_mqtt()
    setup_pm25()
    setup_display()
    mqttc.loop_start()
    myloop()
