# SPDX-FileCopyrightText: 2026 Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Outdoor Light + Battery Logger -- Adafruit ESP32-S2 Feather + VEML7700

Based on Adafruit's "Battery Powered Sun Tracking" guide, extended to also
log the LiPo battery voltage and percent from the Feather's on-board
battery monitor. Copy to CIRCUITPY as code.py.

Reads ambient light in lux and battery level, sends the values to
Adafruit IO feeds, then enters deep sleep to save battery. On wake the
board resets and the script runs again from the top.

Maintenance mode: when the Adafruit IO feed "maintenance" is ON, the board
skips deep sleep and stays awake with WiFi up, so code can be updated over
the CircuitPython web workflow (set CIRCUITPY_WEB_API_PASSWORD in
settings.toml, then browse to http://circuitpython.local/ or the board's IP).
Turn the feed OFF to go back to deep sleep.

Home Assistant: if MQTT_BROKER is set in settings.toml, the readings are
also published to that MQTT broker using Home Assistant MQTT discovery, so
the light, battery voltage and battery percent sensors appear automatically
under one "Sun Tracker" device.

Required hardware:
  - Adafruit ESP32-S2 Feather (on-board LC709203F or MAX17048 monitor)
  - Adafruit VEML7700 Lux Sensor (STEMMA QT / I2C)
  - LiPo battery plugged into the Feather's JST port

Required libraries in the /lib folder:
  - adafruit_veml7700.mpy
  - adafruit_lc709203f.mpy   (older boards, I2C address 0x0B)
  - adafruit_max1704x.mpy    (newer boards, I2C address 0x36)
  - adafruit_requests.mpy
  - adafruit_connection_manager.mpy
  - adafruit_io (folder)
  - adafruit_minimqtt (folder)

Required entries in settings.toml:
  CIRCUITPY_WIFI_SSID = "your-wifi-name"
  CIRCUITPY_WIFI_PASSWORD = "your-wifi-password"
  ADAFRUIT_AIO_USERNAME = "your-aio-username"
  ADAFRUIT_AIO_KEY = "your-aio-key"
  CIRCUITPY_WEB_API_PASSWORD = "your-web-password"  (for maintenance mode)

Optional entries in settings.toml (Home Assistant via MQTT):
  MQTT_BROKER = "192.168.86.x"   (IP of your MQTT broker, e.g. Mosquitto)
  MQTT_PORT = 1883
  MQTT_USERNAME = "mqtt-user"
  MQTT_PASSWORD = "mqtt-password"
"""

import json
import time
from os import getenv

import alarm
import board
import wifi
import adafruit_connection_manager
import adafruit_requests
import adafruit_veml7700
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_HTTP

# -- Settings --
SLEEP_INTERVAL = 300  # seconds between readings (5 minutes)
FEED_NAME = "ambient-light"  # must match your Adafruit IO feed key
VOLTAGE_FEED = "battery-voltage"  # Adafruit IO feed key for battery volts
PERCENT_FEED = "battery-percent"  # Adafruit IO feed key for battery %
MAINT_FEED = "maintenance"  # Adafruit IO toggle: ON = stay awake for updates
HA_NODE = "sun_tracker"  # MQTT topic / device id used for Home Assistant
BATTERY_MAH = 2000  # LC709203F only: 100, 200, 400, 500, 1000, 2000 or 3000


def send(aio, feed, value):
    """Send one value, reporting (not raising) errors so other feeds still go."""
    try:
        aio.send_data(feed, value)
        print(f"Sent {value} to '{feed}'")
    except Exception as e:  # pylint: disable=broad-except
        print(f"ERROR sending to '{feed}': {e}")


# (key in state JSON, name, device_class, unit, precision)
HA_SENSORS = (
    ("lux", "Light", "illuminance", "lx", 1),
    ("voltage", "Battery Voltage", "voltage", "V", 2),
    ("battery", "Battery", "battery", "%", 0),
)


def publish_to_home_assistant(pool, state):
    """Publish readings to MQTT with Home Assistant discovery configs."""
    broker = getenv("MQTT_BROKER")
    if not broker:
        return
    uid = "".join(f"{b:02x}" for b in wifi.radio.mac_address)
    state_topic = f"{HA_NODE}/state"
    device = {
        "identifiers": [f"{HA_NODE}_{uid}"],
        "name": "Sun Tracker",
        "manufacturer": "Adafruit",
        "model": "ESP32-S2 Feather + VEML7700",
    }
    try:
        mqtt = MQTT.MQTT(
            broker=broker,
            port=int(getenv("MQTT_PORT") or 1883),
            username=getenv("MQTT_USERNAME"),
            password=getenv("MQTT_PASSWORD"),
            client_id=f"{HA_NODE}_{uid}",
            socket_pool=pool,
            is_ssl=False,
        )
        mqtt.connect()
        # Discovery configs are retained, so HA finds the sensors even when
        # the board is asleep. Re-sending each wake is cheap and self-healing.
        for key, name, device_class, unit, precision in HA_SENSORS:
            config = {
                "name": name,
                "unique_id": f"{HA_NODE}_{uid}_{key}",
                "state_topic": state_topic,
                "value_template": "{{ value_json.%s }}" % key,
                "device_class": device_class,
                "unit_of_measurement": unit,
                "state_class": "measurement",
                "suggested_display_precision": precision,
                # Mark unavailable if we miss about three wakes in a row
                "expire_after": SLEEP_INTERVAL * 3 + 60,
                "device": device,
            }
            mqtt.publish(
                f"homeassistant/sensor/{HA_NODE}/{key}/config",
                json.dumps(config),
                retain=True,
            )
        mqtt.publish(state_topic, json.dumps(state), retain=True)
        mqtt.disconnect()
        print(f"Published to MQTT {broker}: {state}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"ERROR publishing to MQTT: {e}")


def maintenance_requested(aio):
    """True if the maintenance feed is ON. A missing feed counts as OFF."""
    try:
        value = str(aio.receive_data(MAINT_FEED)["value"]).strip().upper()
    except Exception as e:  # pylint: disable=broad-except
        print(f"Maintenance check failed ({e}) - assuming OFF")
        return False
    return value in ("ON", "1", "TRUE")


def get_battery_monitor(i2c_bus):
    """Return the on-board battery monitor, or None if none is found."""
    while not i2c_bus.try_lock():
        pass
    try:
        addresses = i2c_bus.scan()
    finally:
        i2c_bus.unlock()

    if 0x36 in addresses:
        import adafruit_max1704x  # pylint: disable=import-outside-toplevel

        return adafruit_max1704x.MAX17048(i2c_bus)
    if 0x0B in addresses:
        # pylint: disable=import-outside-toplevel
        from adafruit_lc709203f import LC709203F, PackSize

        monitor = LC709203F(i2c_bus)
        monitor.pack_size = getattr(PackSize, f"MAH{BATTERY_MAH}")
        return monitor
    return None


# -- Hardware setup (once, outside the loop) --
i2c = board.I2C()
veml = adafruit_veml7700.VEML7700(i2c)
try:
    battery = get_battery_monitor(i2c)
except Exception as e:  # pylint: disable=broad-except
    print(f"Battery monitor error: {e}")
    battery = None
if battery is None:
    print("No battery monitor found - is a LiPo plugged in?")
time.sleep(0.5)  # wait for first integration cycle to complete

while True:
    maintenance = False
    try:
        # -- Read the light sensor --
        lux = veml.lux
        print(f"Light: {lux:.1f} lux")

        # -- Read the battery monitor --
        volts = percent = None
        if battery is not None:
            try:
                volts = battery.cell_voltage
                percent = min(battery.cell_percent, 100.0)
                print(f"Battery: {volts:.2f} V, {percent:.1f} %")
            except Exception as e:  # pylint: disable=broad-except
                print(f"Battery read error: {e}")

        # -- Connect to WiFi and send to Adafruit IO --
        if not wifi.radio.ipv4_address:
            wifi.radio.connect(
                getenv("CIRCUITPY_WIFI_SSID"),
                getenv("CIRCUITPY_WIFI_PASSWORD"),
            )
        print(f"WiFi connected - IP: {wifi.radio.ipv4_address}")

        pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
        ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl_context)

        io = IO_HTTP(
            getenv("ADAFRUIT_AIO_USERNAME"),
            getenv("ADAFRUIT_AIO_KEY"),
            requests,
        )

        send(io, FEED_NAME, lux)
        if volts is not None:
            send(io, VOLTAGE_FEED, round(volts, 3))
            send(io, PERCENT_FEED, round(percent, 1))

        state = {"lux": round(lux, 1)}
        if volts is not None:
            state["voltage"] = round(volts, 3)
            state["battery"] = round(percent, 1)
        publish_to_home_assistant(pool, state)

        maintenance = maintenance_requested(io)

    except Exception as e:  # pylint: disable=broad-except
        print(f"ERROR: {e}")

    # -- Maintenance mode: stay awake so the web workflow is reachable --
    if maintenance:
        print("MAINTENANCE mode ON - staying awake for updates")
        print(f"Web workflow: http://{wifi.radio.ipv4_address}/")
        time.sleep(SLEEP_INTERVAL)
        continue  # take another reading and re-check the toggle

    # -- Deep sleep (battery) or wait (USB) --
    print(f"Sleeping {SLEEP_INTERVAL} seconds...")
    time_alarm = alarm.time.TimeAlarm(
        monotonic_time=time.monotonic() + SLEEP_INTERVAL
    )
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
    # On battery: board resets, script runs from the top.
    # On USB: pretend sleep returns here, loop continues.
