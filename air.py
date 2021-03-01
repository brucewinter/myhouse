# -*- coding: utf-8 -*-

# Monitor air quality, graph it to a local LCD, send it to a smarthouse via mqtt, and control a range hood fan for smoke control

# More info at:
#   https://www.youtube.com/brucewinter
#   https://github.com/brucewinter

# Note:
#  Local fan control via switchbot is done from the smart house program via mqtt, for more sophisticated control (e.g. hysteresis)
#  Simple control could be done directly without a smart house. 

#  pip3 install RPI.GPIO
#  pip3 install Adafruit-Blinka
#  pip3 install adafruit_pm25
#  pip3 install adafruit-circuitpython-pm25
#  pip3 install adafruit-circuitpython-sgp30
#  pip3 install adafruit-circuitpython-aqi
#  pip3 install aqi
#  pip3 install python-aqi
#  pip3 install adafruit-circuitpython-rgb_display
#  pip3 install paho-mqtt
#  pip3 install bluepy
   
import os, sys, time, math, subprocess, json, binascii, aqi, requests
import digitalio, board, busio
import adafruit_rgb_display.st7789 as st7789
import paho.mqtt.client as mqtt
#rom   adafruit_rgb_display.rgb import color565
from   adafruit_pm25.i2c import PM25_I2C
from   PIL import Image, ImageDraw, ImageFont

sensor_inst = sys.argv[1]
sensor_pm25   = 1
sensor_sgp30  = 0
sensor_ahtx0  = 0
sensor_bme680 = 0
sensor_scd30  = 0
sensor_switchbot = 0
if (len(sys.argv) > 2):
    if sys.argv[2].find('sgp30')     != -1: sensor_sgp30  = 1
    if sys.argv[2].find('ahtx0')     != -1: sensor_ahtx0  = 1
    if sys.argv[2].find('bme680')    != -1: sensor_bme680 = 1
    if sys.argv[2].find('scd30')     != -1: sensor_scd30  = 1
    if sys.argv[2].find('switchbot') != -1: sensor_switchbot = 1

air_data     = {}
air_data_in  = {}
air_data_bed = {}
air_data_out = {}
air_data_file = 'air_data.json'

start_time = time.time()
watchdog   = 0

# Get previous air data for plots
def load_data():
    global air_data
    print('Loading previous air history')
    if os.path.isfile(air_data_file):
        f = open(air_data_file)
        try: air_data = json.load(f)
        except: print('Unable to load jason data')

    if 'g1' not in air_data: air_data['g1'] = {'aqi_in' : [],  'aqi_out' : [],   'aqi_out_i' : [],  'tvoc' : [], 'co2' : []} 
    if 'g2' not in air_data: air_data['g2'] = {'aqi_in' : [],  'aqi_out' : [],   'aqi_out_i' : [],  'tvoc' : [], 'co2' : []} 
    if 'g3' not in air_data: air_data['g3'] = {'aqi_in' : [],  'aqi_out' : [],   'aqi_out_i' : [],  'tvoc' : [], 'co2' : []} 

#   if 'g1' not in air_data: air_data['g1'] = {'p003' : [],    'pm010s' : [],    'aqi_out' : [],    'aqi_pm25' : [],    'voc' : []}   # 40 min chart
#   if 'g2' not in air_data: air_data['g2'] = {'p003' : [],    'pm010s' : [],    'aqi_out' : [],    'aqi_pm25' : [],    'voc' : []}   # 4 hour chart
#   if 'g3' not in air_data: air_data['g3'] = {'p003' : [0],   'pm010s' : [0],   'aqi_out' : [0],   'aqi_pm25' : [0],   'voc' : [0]}   # max chart
#   if 'g4' not in air_data: air_data['g4'] = {'p003' : [999], 'pm010s' : [999], 'aqi_out' : [999], 'aqi_pm25' : [999], 'voc' : [999]}   # min chart
#   print(air_data)
        
def setup_mqtt():
    global mqttc
    print('air mqtt setup')
    mqttc = mqtt.Client()
    mqttc.on_connect   = on_connect
    mqttc.on_message   = on_message
#   mqttc.on_log       = on_log       # Use this for debugging errors in callbacks
    mqttc.username_pw_set(username='my_name',password='my_password')
    mqttc.connect('192.168.1.123')

def on_connect(mqttc, obj, flags, rc):
    print('air connect rc: '+str(rc))
    mqttc.subscribe('ha/heartbeat')
    mqttc.subscribe('sensor/+')
    mqttc.subscribe('ha/stove')

data = {'td' : ' '}
def on_message(mqttc, obj, msg):
    global air_data_in, air_data_out, air_data_bed, watchdog
    p = msg.payload.decode('utf-8')
#   print('air message: ' + str(msg.topic) + ' = ' + p)
    if msg.topic == 'ha/heartbeat' :
        data['td'] = time.strftime('%a %d %I:%M:%S', time.localtime(int(p) / 1000))
        watchdog = 0
    if msg.topic == 'sensor/Outside Temperature'  : data['tout']    = p
    if msg.topic == 'sensor/Upstairs Temperature' : data['tin']     = p
    if msg.topic == 'sensor/Upstairs Temperature' : data['tin']     = p
    if msg.topic == 'sensor/Air AQI Out I'        : data['aqi_out'] = p
#   if msg.topic == 'sensor/air out'              : data['aqi_out'] = p
    if msg.topic == 'sensor/air in'               : air_data_in  = json.loads(p)
    if msg.topic == 'sensor/air out'              : air_data_out = json.loads(p)
    if msg.topic == 'sensor/air bedroom'          : air_data_bed = json.loads(p)

# Compensate to humidity.  Requires Absolute humidity.  This formula is accurate to within 0.1% over the temperature range –30°C to +35°C
# Absolute Humidity (grams/m3) = 6.112 × e^[(17.67 × T)/(T+243.5)] × rh × 2.1674
    if msg.topic == 'sensor/Upstairs Humidity':
        data['thum'] = p
        tin = float(data['tin'])
        t1 = (17.67 * tin)/(tin + 243.5)
        ah = 6.112 * math.e**t1 * float(p) * 2.1674
        print('Humidity adjustment: t1=%s t=%s h=%s ah=%s' % (t1, data['tin'], p, ah))
        if (sensor_sgp30):
            sgp30.set_iaq_humidity(ah)

    if msg.topic == 'ha/stove' and sensor_switchbot :
        if (1):
            rc = os.system('/mnt/nas/bin/switchbot_stove ' + p)
            print('rc=' + str(rc))
            mac = 'EF:ED:2F:B6:7A:0A' if p == 'on' else 'FA:CC:32:1F:DF:3F'
        else:  # This stopped working, connect fails, not sure why.  Reverted back to system call which still works.
            i = 0
            while (i < 4):
                try:
                    print('Connecting... ' + mac)
                    p = Peripheral(mac, 'random')
                    break
                except:
                    print('Bluetooth connect failed, retry i=' + str(i))
                    i += 1
                    time.sleep(1)
            print('connected')
            hand_service = p.getServiceByUUID('cba20d00-224d-11e6-9fb8-0002a5d5c51b')
            hand = hand_service.getCharacteristics('cba20002-224d-11e6-9fb8-0002a5d5c51b')[0]
            hand.write(binascii.a2b_hex('570100'))
                    
        print('switchbot done')

    
def on_log(mqttc, obj, level, string):
    print(string)

def setup_sensors():
    global pm25, sgp30, bme680, ahtx0, scd30
    reset_pin = None
    i2c = busio.I2C(board.SCL, board.SDA, frequency=100000) # Create library object, use 'slow' 100KHz frequency!
    if (sensor_pm25):
        print('Setting up PM2.5 sensor')
#       pm25 = adafruit_pm25.PM25_I2C(i2c, reset_pin)  # Connect to a PM2.5 sensor over I2C
        pm25 =               PM25_I2C(i2c, reset_pin)  # Connect to a PM2.5 sensor over I2C
    if (sensor_sgp30):
        print('Setting up sgp30')
        import adafruit_sgp30
        sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
        if 'sgp30_baseline_co2' in air_data:
            print('Found SGP30 sensor, setting baseline: co2=%s voc=%s' % (air_data['sgp30_baseline_co2'], air_data['sgp30_baseline_voc']))
            sgp30.iaq_init() # Initialize the IAQ algorithm.
            sgp30.set_iaq_baseline(air_data['sgp30_baseline_co2'], air_data['sgp30_baseline_voc'])

    if (sensor_ahtx0):
        print('Setting up ahtx0 sensor')
        import adafruit_ahtx0
        ahtx0 = adafruit_ahtx0.AHTx0(i2c)
        
    if (sensor_switchbot):
        print('Setting up bluetooth')
        from   bluepy.btle import Peripheral

# The Bosch bme680 sensor is a pain, does not return VOC or AQI, only raw gas resistance (high res -> lower voc)
#   https://learn.adafruit.com/adafruit-bme680-humidity-temperature-barometic-pressure-voc-gas/bsec-air-quality-library
#   The Bosch BSEC library is an all-in-one Arduino library that will get you all the values from the sensor and also perform the AQI calculations. It is not an open source library! You can only use it in Arduino and only with the chipsets supported.
#   https://github.com/adafruit/Adafruit_CircuitPython_BME680/blob/master/adafruit_bme680.py

    if (sensor_bme680):
        print('Setting up bme680 sensor')
        import adafruit_bme680
        bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c)
        bme680.pressure_oversample = 8
        bme680.temperature_oversample = 8
        bme680.humidity_oversample = 8

    if (sensor_scd30):
        print('Setting up scd30 sensor')
        import adafruit_scd30
        while 1:
            try:
                print('Connecting to scd30')
                scd30 = adafruit_scd30.SCD30(i2c)
                break
            except:
                print('Failed, retrying...')
                time.sleep(1)

#       scd30.measurement_interval           = 4
#       scd30.ambient_pressure               = 1100 # Units??
        scd30.altitude                       = 207 # In meters, 680 feet
#       scd30.forced_recalibration_reference = 409 # Use self_calibration instead
        scd30.self_calibration_enabled       = True
        
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



p003_prev = 0
def get_air_data():
    global air_data, pm25_data, p003_prev

#   print('*', end='', flush=True)
    print('*',         flush=True)

    pm25_data = {}
    if (sensor_pm25):
        try:
            pm25_data = pm25.read()
            # print(pm25_data)
        except RuntimeError:
            print('Unable to read from pm25 sensor')
            return

#   pm25_data['co2']  = 0
    pm25_data['tvoc'] = 0

    pm25_data['gas']         = 0
    pm25_data['pressure']    = 0
    pm25_data['humidity']    = 0
    pm25_data['temperature'] = 0


    if (sensor_sgp30):
        try:
            eCO2, TVOC = sgp30.iaq_measure()
            data['eco2'] = 'co2=%d voc=%d' % (eCO2, TVOC)
            # Do not pass data back to house for the first 20 seconds, it give bogus data before it is warmed up
            if (time.time() - start_time) > 20:
#               pm25_data['co2']  = eCO2  # Store in pm25 structure, so we can pass back to mqtt easily
                pm25_data['eco2'] = eCO2
                pm25_data['tvoc'] = TVOC
                co2_base, voc_base = sgp30.baseline_eCO2, sgp30.baseline_TVOC
                air_data['sgp30_baseline_co2'], air_data['sgp30_baseline_voc'] = co2_base, voc_base
                baseline = 'base co2=%d voc=%d' % (co2_base, voc_base)
                print(data['eco2'] + ' ' + baseline)
        except RuntimeError:
            print('Unable to read from sgp30 sensor')
            return

       
    pm010s = pm25_data.get('pm10 standard', 0)
    pm025s = pm25_data.get('pm25 standard', 0)
    pm100s = pm25_data.get('pm100 standard', 0)
    pm010e = pm25_data.get('pm10 env', 0)
    pm025e = pm25_data.get('pm25 env', 0)
    pm100e = pm25_data.get('pm100 env', 0)
    p003   = pm25_data.get('particles 03um', 0)
    p005   = pm25_data.get('particles 05um', 0)
    p010   = pm25_data.get('particles 10um', 0)
    p025   = pm25_data.get('particles 25um', 0)
    p050   = pm25_data.get('particles 50um', 0)
    p100   = pm25_data.get('particles 100um', 0)

    if (sensor_ahtx0):
        pm25_data['temperature'] = 32 + (9/5)*ahtx0.temperature
        pm25_data['humidity']    = ahtx0.relative_humidity
        print("ahtx0  temperature: %0.1f F, humidity=%3i" % (pm25_data['temperature'], pm25_data['humidity']))
        
    if (sensor_bme680):
        try:
            pm25_data['gas']         = bme680.gas
            pm25_data['pressure']    = bme680.pressure / 33.8639 # Convert from kPa to inHg (inches of mercury)
            pm25_data['humidity']    = bme680.humidity
            pm25_data['temperature'] = 32 + (9/5)*bme680.temperature
            print("bme680 temperature: %0.1f F, humidity=%3i" % (pm25_data['temperature'], pm25_data['humidity']))
        except RuntimeError:
            print('Unable to read from bme680 sensor')
            return
    if (sensor_scd30):
        try:
            if scd30.data_available:
                pm25_data['temperature'] = 32 + (9/5)*scd30.temperature
                pm25_data['humidity']    = int(scd30.relative_humidity)
                pm25_data['co2']         = int(scd30.CO2)
                data['co2'] = 'co2=%d' % (pm25_data['co2'])
                print("scd30  temperature: %0.1f F, humidity=%3i, co2=%4i" %
                      (pm25_data['temperature'], pm25_data['humidity'], pm25_data['co2']))

        except RuntimeError:
            print('Unable to read from sdc30 sensor')
            return

         
    
    print('#', end='', flush=True)

    # Avoid abend with values > 500:    File "/home/pi/.local/lib/python3.7/site-packages/aqi/algos/base.py", line 91, in iaqi   (aqilo, aqihi) = self.piecewise['aqi'][idx]  IndexError: list index out of range
    if (pm025s < 500):
        aqi_pm10 = int(aqi.to_iaqi(aqi.POLLUTANT_PM10, pm010s, algo=aqi.ALGO_EPA))
        aqi_pm25 = int(aqi.to_iaqi(aqi.POLLUTANT_PM25, pm025s, algo=aqi.ALGO_EPA))
        pm25_data['aqi pm10'] = aqi_pm10
        pm25_data['aqi pm25'] = aqi_pm25
    else: #  use previous data
        aqi_pm10 = pm25_data['aqi pm10']
        aqi_pm25 = pm25_data['aqi pm25']
        
    aqi_in     = int(air_data_in.get( 'aqi pm25', 0))
    aqi_bed    = int(air_data_bed.get('aqi pm25', 0))
    aqi_out    = int(air_data_out.get('aqi pm25', 0))
    aqi_out_i  = int(data.get('aqi_out', 0))
    tvoc       = pm25_data['tvoc']
    gas        = pm25_data['gas']
    
    data['rpms'] = 'S: ' + str(pm010s) + ' ' + str(pm025s) + ' ' + str(pm100s)
    data['aqi']  = 'A: I:' + str(aqi_in) + ' B:' + str(aqi_bed) + ' O:' + str(aqi_bed) + ' ' + str(aqi_out_i)
    data['rp1']  = 'P: ' + str(p003)   + ' ' + str(p010)   + ' ' + str(p100) 
#   data['rp1']  = 'P: ' + str(p003)   + ' ' + str(p005)   + ' ' + str(p010) 
    data['rp2']  = 'P: ' + str(p025)   + ' ' + str(p050)   + ' ' + str(p100)


    p003  = int(p003) # Is always > 10, so need for floating point
    p003l = int(10 * math.log10(p003)) if p003 > 0 else 0
    pm010sl = 220 if pm010s > 220 else pm010s
    
    t = int(time.time())

# Look for rapid increases, so we can detect smoke quickly
#   if 'p003_prev' not in locals(): p003_prev = 0   # This did not work :( Use global instead
    p003d = p003 - p003_prev
    p003_prev = p003
    print('p003=' + str(p003) + ' p003d=' + str(p003d))
    
    if t % 5 == 0 or p003d > 100 :
        mqttc.publish('sensor/air ' + sensor_inst, json.dumps(pm25_data))
        print('mqtt published to: sensor/air ' + sensor_inst)
    if (sensor_inst == 'out' and t % 60 == 0) :
        publish_data(pm025s, pm010s, pm100s)

    if t %      10 == 0 : store_data('g1', aqi_in, aqi_out, aqi_out_i, tvoc)  # Data for a 40 min  graph:  240 / 40 =  6 readings per minute, 1 every 10 seconds.
    if t %      60 == 0 : store_data('g2', aqi_in, aqi_out, aqi_out_i, tvoc)  # Data for a  4 hour graph:  240 / 4*60 = 1 readings per minute
    if t % (60*24) == 0 : store_data('g3', aqi_in, aqi_out, aqi_out_i, tvoc)  # Data for a  4 day  graph:  240 / 96   hours = 2.5   per hour, 1 for every 24 minutes

    
    if t % (60*5) == 0 :
        print('Saving air_data')
        with open(air_data_file, 'w') as f:
            json.dump(air_data, f, sort_keys=True, indent=4)
        f.close()

        
# No longer using this max/min data
#   if p003      > air_data['g4']['p003'][-1]     :  air_data['g4']['p003'][-1]    = p003
#   if pm010s    > air_data['g4']['pm010s'][-1]   :  air_data['g4']['pm010s'][-1]  = pm010s
#   if aqi_pm25  > air_data['g4']['aqi_pm25'][-1] :  air_data['g4']['aqi_pm25'][-1]  = aqi_pm25
#   if aqi_out   > air_data['g4']['aqi_out'][-1]  :  air_data['g4']['aqi_out'][-1] = aqi_out 
#   if p003      < air_data['g4']['p003'][-1]     :  air_data['g4']['p003'][-1]    = p003
#   if pm010s    < air_data['g4']['pm010s'][-1]   :  air_data['g4']['pm010s'][-1]  = pm010s 
#   if aqi_pm25  < air_data['g4']['aqi_pm25'][-1] :  air_data['g4']['aqi_pm25'][-1]  = aqi_pm25
#   if aqi_out   < air_data['g4']['aqi_out'][-1]  :  air_data['g4']['aqi_out'][-1] = aqi_out

def store_data(chart, aqi_in, aqi_out, aqi_out_i, tvoc):
    air_data[chart]['aqi_in'].append(aqi_in)
    air_data[chart]['aqi_out'].append(aqi_out)
    air_data[chart]['aqi_out_i'].append(aqi_out_i)
    air_data[chart]['tvoc'].append(tvoc)
    
    if len(air_data[chart]['aqi_in']) > 240:
        air_data[chart]['aqi_in']    = air_data[chart]['aqi_in'][1:]
        air_data[chart]['aqi_out']   = air_data[chart]['aqi_out'][1:]
        air_data[chart]['aqi_out_i'] = air_data[chart]['aqi_out_i'][1:]
        air_data[chart]['tvoc']      = air_data[chart]['tvoc'][1:]

def store_data_old(chart):
    air_data[chart]['p003'].append(p003l)
    air_data[chart]['pm010s'].append(pm010sl)
    air_data[chart]['aqi_pm25'].append(aqi_pm25)
    air_data[chart]['aqi_out'].append(aqi_out)
    air_data[chart]['voc'].append(pm25_data['tvoc'])
    if len(air_data[chart]['pm010s']) > 240:
        air_data[chart]['p003']    = air_data[chart]['p003'][1:]
        air_data[chart]['pm010s']  = air_data[chart]['pm010s'][1:]
        air_data[chart]['aqi_pm25']  = air_data[chart]['aqi_pm25'][1:]
        air_data[chart]['aqi_out'] = air_data[chart]['aqi_out'][1:]
        air_data[chart]['voc']     = air_data[chart]['voc'][1:]


def display_data():
    draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))     # Clear screen

    if 'aqi' not in data: return   # Skip if we do not have data yet on startup
    
    if not buttonA.value :
        display_data2()
    elif not buttonB.value :
        display_data3()
    else :
        display_data1()
        
    my_disp.image(image, rotation)     # Display image.

    
def display_data1():
    global air_data

    plot_data(air_data['g1']['aqi_in'],    1, '#FF0000')
    plot_data(air_data['g1']['aqi_out'],   1, '#00FF00')
#   plot_data(air_data['g1']['aqi_out_i'], 1, '#0000FF')
    plot_data(air_data['g1']['co2'],      .5, '#0000FF')
    plot_data(air_data['g1']['tvoc'],     .1, '#888888')

    to = data.get('tout', 0)
    ti = data.get('tin', 0)
    temps = 'T In/Out: ' + str(ti) + '/' + str(to)
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
#    draw.text((x, y), data['rpms'], font=font, fill='#FFFFFF')
#    y += fontsize
    draw.text((x, y), data['aqi'], font=font, fill='#FFFFFF')
    y += fontsize
    draw.text((x, y), data['rp1'], font=font, fill='#FFFFFF')
#    y += fontsize
#     draw.text((x, y), data['rp2'], font=font, fill='#FFFFFF')
    y += fontsize
    if (sensor_sgp30):
        draw.text((x, y), data['eco2'], font=font, fill='#FFFFFF')
        y += fontsize
    if (sensor_scd30 and 'co2' in data):
        draw.text((x, y), data['co2'], font=font, fill='#FFFFFF')
        y += fontsize
#    draw.text((x, y), cpu, font=font, fill='#0000FF')
#    y += fontsize
   
def display_data2():
    global air_data
    plot_data(air_data['g2']['aqi_in'],    1, '#FF0000')
    plot_data(air_data['g2']['aqi_out'],   1, '#00FF00')
#   plot_data(air_data['g2']['aqi_out_i'], 1, '#0000FF')
    plot_data(air_data['g2']['co2'],      .5, '#0000FF')
    plot_data(air_data['g2']['tvoc'],     .1, '#888888')

#    plot_data(air_data['g2']['p003'],      1, '#FF0000')  # red   4 hour chart
#    plot_data(air_data['g2']['pm010s'],    1, '#00FF00')  # green 4 hour chart
#    plot_data(air_data['g2']['aqi_pm25'],  1, '#0000FF')  # Blue  4 hour chart
#    plot_data(air_data['g2']['aqi_out'],   1, '#00FFFF')  #    
#    plot_data(air_data['g2']['voc'],      .1, '#888888')  # 

def display_data3():
    global air_data
    plot_data(air_data['g3']['aqi_in'],    1, '#FF0000')
    plot_data(air_data['g3']['aqi_out'],   1, '#00FF00')
#   plot_data(air_data['g3']['aqi_out_i'], 1, '#0000FF')
    plot_data(air_data['g3']['co2'],      .5, '#0000FF')
    plot_data(air_data['g3']['tvoc'],     .1, '#888888')


def display_data4():
    global air_data
    plot_data(air_data['g3']['p003'],    0.2, '#FF0000') # 4 day max/min charts
    plot_data(air_data['g3']['pm010s'],  0.5, '#00FF00') # 
    plot_data(air_data['g4']['p003'],    0.2, '#FF8888') # 
    plot_data(air_data['g4']['pm010s'],  0.5, '#88FF88') # 
    plot_data(air_data['g3']['aqi_pm25'],  1, '#0000FF') # 
    plot_data(air_data['g3']['aqi_out'],   1, '#00FFFF') # 
    plot_data(air_data['g4']['aqi_pm25'],  1, '#FF0000') # 
    plot_data(air_data['g4']['aqi_out'],   1, '#FFFF00') # 

def plot_data(data, scale, color):
    x  = 0
    yp = 0
    for i in data:
        x = x + 1
        y = bottom - int(scale * i)
        if x > 1:
            draw.line((x-1, yp, x, y), width=1, fill=(color))
        yp = y
        if x % 60 == 0 :   # Draw 4 grid lines
            draw.line((x, bottom, x, 150), width=1, fill=('#FFFFFF'))
            
def plot_data_bar(data, scale, color):
    x = 0
    for i in data:
        x = x + 1
        y = bottom - int(scale * i)
        draw.line((x, bottom, x, y), width=1, fill=(color))
        if x % 60 == 0 :   # Draw 4 grid lines
            draw.line((x, bottom, x, 150), width=1, fill=('#FFFFFF'))

# From: https://aqicn.org/data-feed/upload-api/
def publish_data(pm25, pm10, pm100):
    sensorReadings = [   
        {'specie':'pm25',  'value': pm25},  
        {'specie':'pm10',  'value': pm10},  
        {'specie':'pm100', 'value': pm100}  
    ] 
    station = { 
        'id':    "starcross-01",  
        'name':   "Starcross",  
        'location':  { 
            'latitude': 33.437475,
            'longitude': -86.779897
        } 
    } 
    userToken = "409c9c0b706ab11a79b1a80b21355d1701bf52d4"
    
    params = {'station':station,'readings':sensorReadings,'token':userToken}  
    try:
        request = requests.post( url = "https://aqicn.org/sensor/upload/",  json = params)
        data = request.json()  
        if data["status"]!="ok": 
            print("Something went wrong: %s" % data) 
        else: 
            print("Data successfully posted: %s"%data)
    except:
        print('Unable to publish data to aqicn.org')



def myloop():
    global watchdog
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
#       print(ts)
        if ts > 0: time.sleep(ts)
        watchdog += 1
        if watchdog > 1: print(watchdog,    flush=True)
        if watchdog > 500:
            print(sensor_inst + ' air watchdog heartbeat missing, rebooting')
            os.system('sudo reboot')
            
        
if __name__ == '__main__':
    load_data()
    setup_mqtt()
    setup_sensors()
    setup_display()
    mqttc.loop_start()
    myloop()
