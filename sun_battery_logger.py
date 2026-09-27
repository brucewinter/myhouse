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
"""

import time
from os import getenv

import alarm
import board
import wifi
import adafruit_connection_manager
import adafruit_requests
import adafruit_veml7700
from adafruit_io.adafruit_io import IO_HTTP

# -- Settings --
SLEEP_INTERVAL = 300  # seconds between readings (5 minutes)
FEED_NAME = "ambient-light"  # must match your Adafruit IO feed key
VOLTAGE_FEED = "battery-voltage"  # Adafruit IO feed key for battery volts
PERCENT_FEED = "battery-percent"  # Adafruit IO feed key for battery %
BATTERY_MAH = 2000  # LC709203F only: 100, 200, 400, 500, 1000, 2000 or 3000


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

        io.send_data(FEED_NAME, lux)
        if volts is not None:
            io.send_data(VOLTAGE_FEED, round(volts, 3))
            io.send_data(PERCENT_FEED, round(percent, 1))
        print("Sent to Adafruit IO!")

    except Exception as e:  # pylint: disable=broad-except
        print(f"ERROR: {e}")

    # -- Deep sleep (battery) or wait (USB) --
    print(f"Sleeping {SLEEP_INTERVAL} seconds...")
    time_alarm = alarm.time.TimeAlarm(
        monotonic_time=time.monotonic() + SLEEP_INTERVAL
    )
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
    # On battery: board resets, script runs from the top.
    # On USB: pretend sleep returns here, loop continues.
