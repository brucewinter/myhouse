
// This Arduino sketch reads various sensors (DS18B20 "1-Wire" digital temp sensors, thermistor, sunlight) and passes data to Xively cloud 

#include <OneWire.h>
#include <DallasTemperature.h>
//#include <Wire.h>
#include <SimpleTimer.h>

#include <Bridge.h>
#include <YunServer.h>
#include <YunClient.h>
#include <Process.h>
#include "passwords.h"

// Data wire is plugged into pin 3 on the Arduino
#define RELAY1 10
#define RELAY2 11
#define ONE_WIRE_BUS1 5
#define ONE_WIRE_BUS2 12
#define ONE_WIRE_BUS3 3

// Setup a oneWire instance to communicate with any OneWire devices.  Multiple sensors can be on one bus.
OneWire oneWire1(ONE_WIRE_BUS1);
OneWire oneWire2(ONE_WIRE_BUS2);
OneWire oneWire3(ONE_WIRE_BUS3);

// Pass our oneWire reference to Dallas Temperature.
DallasTemperature sensors1(&oneWire1);
DallasTemperature sensors2(&oneWire2);
DallasTemperature sensors3(&oneWire3);

// Assign the addresses of your 1-Wire temp sensors. See the tutorial on how to obtain these addresses:
// http://www.hacktronics.com/Tutorials/arduino-1-wire-address-finder.html

DeviceAddress Thermometer1 = { 0x28, 0xC3, 0x25, 0x03, 0x04, 0x00, 0x00, 0xE4 };
DeviceAddress Thermometer2 = { 0x28, 0x28, 0x4A, 0x03, 0x04, 0x00, 0x00, 0x4B };
DeviceAddress Thermometer3 = { 0x28, 0xA9, 0x4E, 0x03, 0x04, 0x00, 0x00, 0x89 };

SimpleTimer timer;

String sensor_data = "";

YunServer server;
String server_startString;
long server_hits = 0;
long dead_switch_counter = 0;

void setup(void)
{
  Serial.begin(9600);
  Serial.println("Starting setup");
  Bridge.begin();
  server.listenOnLocalhost();
  server.begin();
  server_startString = my_date();

  sensors1.begin();
  sensors2.begin();
  sensors3.begin();
  // set the resolution to 12 bit (maybe 10 bit is good enough?)
  sensors1.setResolution(Thermometer1, 11);
  sensors2.setResolution(Thermometer2, 11);
  sensors3.setResolution(Thermometer3, 11);

  pinMode(RELAY1, OUTPUT);
  pinMode(RELAY2, OUTPUT);

  digitalWrite(RELAY1, HIGH);
  digitalWrite(RELAY2, HIGH);

  timer.setInterval(    100, server_read);
  timer.setInterval(  60000, sensors_read);
  timer.setInterval(  60000, dead_switch);

  Serial.println("Done with setup");

  sensors_read;  // Read data right away
}

void server_read(void) {
  YunClient client = server.accept();
  if (client) {
    serveClient(client);
  }
}

// Turn pump relay off in case wi-fi goes down and heat stops comming in.  Could reset the dead_switch counter periodcally from mh, but this probably will not falsely turn off too often.
void dead_switch(void) {
  float temp2f = sensors2.getTempF(Thermometer2);
  float temp3f = sensors3.getTempF(Thermometer3);
  float td23 = temp2f-temp3f;
  if (td23 < 0) {
    dead_switch_counter++;
  }
  else {
    dead_switch_counter = 0;
  }
  if (dead_switch_counter > 15) {
    dead_switch_counter = 0;
    digitalWrite(RELAY1, HIGH);
  }
}


void serveClient (YunClient client) {
    String command = client.readString();
    command.trim();        //kill whitespace
    Serial.println(command);
    if (command == "temperature") {
      String timeString = my_date();
      Serial.println(timeString);
      client.print("Current time on the Yún: ");
      client.println(timeString);
      client.print("This sketch has been running since ");
      client.println(server_startString);
      client.print("Hits so far: ");
      client.println(server_hits);
      client.print("<br>Sensor data: ");
      client.print(sensor_data);
    }
    else if (command == "data") {
      client.print(sensor_data);
    }
    else if (command == "relay1_on") {
      digitalWrite(RELAY1, LOW);
      client.print("Relay 1 on");
    }
    else if (command == "relay1_off") {
      digitalWrite(RELAY1, HIGH);
      client.print("Relay 1 off");
    }
    else if (command == "relay2_on") {
      digitalWrite(RELAY2, LOW);
      client.print("Relay 2 on");
    }
    else if (command == "relay2_off") {
      digitalWrite(RELAY2, HIGH);
      client.print("Relay 2 off");
    }

    
    else {
      Serial.println("Unknown command");
      client.print("<br>Unknown command");
    } 
    // Close connection and free resources.
    client.stop();
    server_hits++;
}

void sensors_read(void) {
  Serial.print("Getting temperatures...");
  sensors1.requestTemperatures();
  sensors2.requestTemperatures();
  sensors3.requestTemperatures();
  Serial.print("done\n\r");

  //float temp1f = DallasTemperature::toFahrenheit(sensors1.getTempC(Thermometer1));
  float temp1f = sensors1.getTempF(Thermometer1);
  float temp2f = sensors2.getTempF(Thermometer2);
  float temp3f = sensors3.getTempF(Thermometer3);

  // Sometimes we get -196.6 degree readings (noise on 1 wire bus?), so reread if needed
  int i = 4;
  while (i > 0) {
    i--;
    if (temp1f < -50) {
      temp1f = sensors1.getTempF(Thermometer1);
    }
    if (temp2f < -50) {
      temp2f = sensors2.getTempF(Thermometer2);
    }
    if (temp3f < -50) {
      temp3f = sensors3.getTempF(Thermometer3);
    }
  }
//  if (temp1f < -50 or temp2f < -50 or temp3f < -50) {
//    return;
//  }

  float temp4f = Thermister(analogRead(A1));
  float sunf = analogRead(A2);
  int sun = 100 * sunf / 780; // Normalize, min=0, max=780.

  int relay1_state = digitalRead(RELAY1);
  int relay2_state = digitalRead(RELAY2);
  if (relay1_state == 1) {
    relay1_state = 0;
  } else {
    relay1_state = 1;
  }
  if (relay2_state == 1) {
    relay2_state = 0;
  } else {
    relay2_state = 1;
  }

  sensor_data = "";
  sensor_data += "Pump,";
  sensor_data += relay1_state;
  sensor_data += "\nSun,";
  sensor_data += sun;
  sensor_data += "\nTempTube,";
  sensor_data += temp1f;
  sensor_data += "\nTempInlet,";
  sensor_data += temp2f;
  sensor_data += "\nTempTub,";
  sensor_data += temp3f;
  sensor_data += "\nTempOutdoor,";
  sensor_data += temp4f;
  sensor_data += "\nTD_Tube_Inlet,";
  sensor_data += temp1f-temp2f;
  sensor_data += "\nTD_Inlet_Tub,";
  sensor_data += temp2f-temp3f;
  Serial.print("Data:");
  Serial.print(sensor_data);
  
  Serial.print(sensor_data); 
  // If NotANumber, something went wrong
  if (isnan(temp2f)) {
    Serial.println("Failed to read data");
  } 
  else {
    xively_write();
  }
  
}

void xively_write() {
  String apiString = "X-ApiKey: ";
  apiString += APIKEY;

  String url = "https://api.xively.com/v2/feeds/";
  url += FEEDID;
  url += ".csv";

  Process xively;
  Serial.print("\nSending data... ");
  xively.begin("curl");
  xively.addParameter("-k");
  xively.addParameter("--request");
  xively.addParameter("PUT");
  xively.addParameter("--data");
  xively.addParameter(sensor_data);
  xively.addParameter("--header");
  xively.addParameter(apiString); 
  xively.addParameter(url);
  xively.run();
  Serial.print("done!");

  while (xively.available()>0) {
    char c = xively.read();
    Serial.write(c);
  }
}

double Thermister(int RawADC) {
  double Temp;
  Temp = log(((10240000 / RawADC) - 10000));
  Temp = 1 / (0.001129148 + (0.000234125 + (0.0000000876741 * Temp * Temp )) * Temp );
  Temp = Temp - 273.15;            // Convert Kelvin to Celcius
  Temp = (Temp * 9.0) / 5.0 + 32.0; // Convert Celcius to Fahrenheit
  return Temp;
}

String my_date() {
  String date; 
  Process startTime;
  startTime.runShellCommand("date");
  while (startTime.available()) {
    char c = startTime.read();
    date += c;
  }
  return date;
}

void loop() {
  timer.run();
}

