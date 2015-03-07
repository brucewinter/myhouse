
// Read air sensor data and post to Xively 
// Server example from:  Info at: http://arduino.cc/en/Tutorial/TemperatureWebPanel

#include <Bridge.h>
#include <YunServer.h>
#include <YunClient.h>
#include <Process.h>
#include "passwords.h"

// Disabled for now, not enough memory.  Skip humidity, add another one wire temp sensor
//#include "DHT.h" 

// Do the IR send thing for fan control.   Note, IR LED must be connected to Pin 3, as it has PWM option, easiest to do the 38khz IR transmition on 
#include <IRremote.h>
IRsend irsend;

// Not enough memory in 28k bytes for both light and 1-wire temp sensors :(
//#include <Wire.h>
//#include <Digital_Light_TSL2561.h>

#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS1 4
#define PIN_DUST 8 
//#define PIN_DHT A0 
#define VREF 4.95
//#define DHTTYPE DHT22   // DHT 22  (AM2302)

//DHT dht(PIN_DHT, DHTTYPE);

const unsigned long interval_ms = 60000; 
unsigned       long time_ms = 0;  
unsigned       long dust_duration_total = 0;
String sensor_data = "";
String other_data = "";

YunServer server;
long server_hits = 0;
long xively_writes = 0;

// Setup a oneWire instance to communicate with any OneWire devices.  Multiple sensors can be on one bus.
OneWire oneWire1(ONE_WIRE_BUS1);
DallasTemperature sensors1(&oneWire1);

// Assign the addresses of your 1-Wire temp sensors. See the tutorial on how to obtain these addresses:
// http://www.hacktronics.com/Tutorials/arduino-1-wire-address-finder.html

DeviceAddress Thermometer1 = {0x28, 0x30, 0xE9, 0xF1, 0x05, 0x00, 0x00, 0x11};  // A
DeviceAddress Thermometer2 = {0x28, 0x37, 0x62, 0xF2, 0x05, 0x00, 0x00, 0xA7};  // B
DeviceAddress Thermometer3 = {0x28, 0x7B, 0xD4, 0xF2, 0x05, 0x00, 0x00, 0x7C};  // C
DeviceAddress Thermometer4 = {0x28, 0x03, 0x02, 0xF3, 0x05, 0x00, 0x00, 0x08};  // D
DeviceAddress Thermometer5 = {0x28, 0x49, 0x18, 0xF2, 0x05, 0x00, 0x00, 0xFC};  // E

void setup() {
  Serial.begin(9600);
  Serial.println("Send air sensor data to Xively");
  Bridge.begin();
  server.listenOnLocalhost();
  server.begin();
//  dht.begin();               // Humidty and Temp sensor
  pinMode(PIN_DUST, INPUT);  // Dust sensor
//  Wire.begin();              // Light sensor
//  TSL2561.init();            // Light sensor
  time_ms = millis();
  sensors1.begin();
  sensors1.setResolution(Thermometer1, 11);     // set the resolution to 12 bit (maybe 10 bit is good enough?)
  sensors1.setResolution(Thermometer2, 11);     // set the resolution to 12 bit (maybe 10 bit is good enough?)
  sensors1.setResolution(Thermometer3, 11);     // set the resolution to 12 bit (maybe 10 bit is good enough?)
  sensors1.setResolution(Thermometer4, 11);     // set the resolution to 12 bit (maybe 10 bit is good enough?)
  sensors1.setResolution(Thermometer5, 11);     // set the resolution to 12 bit (maybe 10 bit is good enough?)
  Serial.println("Done with setup");
}

void(* resetFunc) (void) = 0; //declare reset function @ address 0

void loop() {
  long duration = pulseIn(PIN_DUST, LOW);   // pulseIn returns ms signal was low since last call
  dust_duration_total = dust_duration_total+duration;

  long now = millis();
  if (now - time_ms >= interval_ms) {
    updateData();
    time_ms = now;
  }

  YunClient client = server.accept();
  if (client) {
    serveClient(client);
  }
  
  delay(100);
}

void serveClient (YunClient client) {
    String command = client.readString();
    command.trim();        //kill whitespace
    Serial.println(command);
    if (command == "temperature") {
      client.print("<br>Sensor data: ");
      client.print(sensor_data);
      client.print("<br>Other data: ");
      client.print(other_data);
      client.print("<br>Hits so far: ");
      client.print(server_hits);
    }
    else if (command == "fan_on") {  
      irsend.sendNEC(0xFFC03F, 32); // SPT fan on/off
      irsend.sendNEC(0xFFF00F, 32); // SPT fan osc
    }
    else if (command == "fan_power") {  
      irsend.sendNEC(0xFFC03F, 32); // SPT fan on/off
    }
    else if (command == "fan_speed") {  
       irsend.sendNEC(0xFFD02F, 32);  
    }
    else if (command == "fan_osc") {  
      irsend.sendNEC(0xFFF00F, 32);  
    }
    else if (command == "fan_timer") {  
      irsend.sendNEC(0xFFE01F, 32); 
    }
    else if (command == "fan_mist") {  
      irsend.sendNEC(0xFFC837, 32); 
    }
    else {
      Serial.println("Unknown command");
      client.print("<br>Unknown command");
    } 

    // Close connection and free resources.
    client.stop();
    server_hits++;
}

void updateData () {
  // Measure dust
  float ratio = dust_duration_total/(interval_ms*10.0);  // Integer percentage 0=>100
  float dust  = 1.1*pow(ratio,3)-3.8*pow(ratio,2)+520*ratio+0.62; // using spec sheet curve
  dust_duration_total = 0;
  
  // Reading temperature or humidity takes about 250 milliseconds!
    float h; 
    float t;
//  float h = dht.readHumidity();
//  float t = Fahrenheit(dht.readTemperature());
    
  // Measure light
//  Serial.print("getting light ... ");
//  TSL2561.getLux();
//  int l = TSL2561.calculateLux(0,0,1);
//  Serial.print("The Light value is: ");
//  Serial.println(l);
  
  // Measure 1-wire temps
  sensors1.requestTemperatures();
  float tww1 = sensors1.getTempF(Thermometer1);
  float tww2 = sensors1.getTempF(Thermometer2);
  float tww3 = sensors1.getTempF(Thermometer3);
  float tww4 = sensors1.getTempF(Thermometer4);
  float tww5 = sensors1.getTempF(Thermometer5);
 
  // Send data
  int yunnum = 2;
  sensor_data = "";
  sensor_data += "\nTemperature"; sensor_data += yunnum;  sensor_data += ",";
  sensor_data += t;
  sensor_data += "\nHumidity";   sensor_data += yunnum;  sensor_data += ",";
  sensor_data += h;
  sensor_data += "\nDust";       sensor_data += yunnum;  sensor_data += ",";
  sensor_data += dust;
//  sensor_data += "\nLight";      sensor_data += yunnum;  sensor_data += ",";
//  sensor_data += l;
  
  sensor_data += "\nTempWW1,"; sensor_data += tww1;
  sensor_data += "\nTempWW2,"; sensor_data += tww2;
  sensor_data += "\nTempWW3,"; sensor_data += tww3;
  sensor_data += "\nTempWW4,"; sensor_data += tww4;
  sensor_data += "\nTempWW5,"; sensor_data += tww5;
    
  Serial.print(sensor_data); 
  // If NotANumber, something went wrong
  if (isnan(t) || isnan(h) || isnan(dust)) {
    Serial.println("Failed to read data");
  } 
  else {
    sendData();
  }
}

void sendData() {
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
  Serial.println("done!");
  xively_writes++;
  other_data = " my xively results: ";
  other_data += xively_writes;
  while (xively.available()>0) {
    char c = xively.read();
    Serial.write(c);
    other_data += c;
  }
  other_data += ".";
}

//Celsius to Fahrenheit conversion
//double Fahrenheit(double celsius) {
//  return 1.8 * celsius + 32;
//}
