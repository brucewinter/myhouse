#!/bin/sh
#
# description: Starts and stops the tts_mqtt daemon
#
### BEGIN INIT INFO
# Provides: tts_mqtt
# Required-Start: $network $syslog $remote_fs
# Required-Stop: $network
# Default-Start: 2 3 5
# Default-Stop: 0 1 6
# Short-Description: tts_mqtt daemon
# Description: Start or stop the tts_mqtt daemon
### END INIT INFO

TTS_MQTT_BIN=/home/pi/bin/tts_mqtt
test -x $TTS_MQTT_BIN || { echo "$TTS_MQTT_BIN not avaible";
        if [ "$1" = "stop" ]; then exit 0;
        else exit 5; fi; }

RETVAL=0

case "$1" in
  start)
        echo -n "Starting tts_mqtt daemon now "
        sudo -u pi $TTS_MQTT_BIN &   # Add your parameters after
        ;;
  stop)
        echo -n "Shutting down tts_mqtt daemon "
        killall tts_mqtt
        ;;
  restart)
        echo -n "Restarting tts_mqtt daemon "
        killall tts_mqtt
        sudo -u pi $TTS_MQTT_BIN  &  # Add your parameters after
        ;;
  status)
        echo -n "Checking for tts_mqtt service now "
        ;;
  *)
        echo $"Usage: $0 {start|stop|status|try-restart|restart|force-reload|reload}"
        exit 1
esac
