
// Control and monitor the pool via yun5.  Uses DS18B20 "1-Wire" digital temp sensors and passes data to Xively cloud f

#include <OneWire.h>
#include <DallasTemperature.h>
//#include <Digital_Light_TSL2561.h>
#include <SimpleTimer.h>

#include <Bridge.h>
#include <YunServer.h>
#include <YunClient.h>
#include <Process.h>
#include "passwords.h"

// Data wire is plugged into pin 3 on the Arduino
#define RELAY1 2
#define RELAY2 3
#define RELAY3 4
#define RELAY4 5
#define RELAY5 6
#define RELAY6 7
#define IMP_RX 8
#define IMP_TX 9
#define RELAY7 10
#define RELAY8 11
 
#define DI1 12
#define DI2 13 
#define DI3 A1 
#define DI4 A2 

#define ONE_WIRE_BUS1 A3

// Setup a oneWire instance to communicate with any OneWire devices.  Multiple sensors can be on one bus.
OneWire oneWire1(ONE_WIRE_BUS1);

// Pass our oneWire reference to Dallas Temperature. 
DallasTemperature sensors1(&oneWire1);

// Assign the addresses of your 1-Wire temp sensors. See the tutorial on how to obtain these addresses:
// http://www.hacktronics.com/Tutorials/arduino-1-wire-address-finder.html

//DeviceAddress Thermometer1 = { 0x28, 0xC3, 0x25, 0x03, 0x04, 0x00, 0x00, 0xE4 };
//DeviceAddress Thermometer2 = { 0x28, 0x28, 0x4A, 0x03, 0x04, 0x00, 0x00, 0x4B };
//DeviceAddress Thermometer3 = { 0x28, 0xA9, 0x4E, 0x03, 0x04, 0x00, 0x00, 0x89 };
DeviceAddress Thermometer1 = { 0x28, 0x30, 0x4D, 0x03, 0x04, 0x00, 0x00, 0xE0 };
DeviceAddress Thermometer2 = { 0x28, 0xBC, 0x17, 0x03, 0x04, 0x00, 0x00, 0x5F };
DeviceAddress Thermometer3 = { 0x28, 0x5F, 0x10, 0x03, 0x04, 0x00, 0x00, 0x7E };

SimpleTimer timer;  // http://playground.arduino.cc/Code/SimpleTimer
String sensor_data = "";
YunServer server;
String server_startString;
long server_hits = 0;

char data[100];

int cover_state; // 1=open 2=close 3=opening 4=closing
int cover_relay_timer;
int cover_limit_timer;
int cover_limit_honor;
int button_longpress;
int button_longpress_timer;
int relay1_state;
int relay2_state;
int relay3_state;
int relay4_state;
int relay5_state;
int relay6_state;
int relay7_state;
int relay8_state;
int di1_state;
int di2_state;
int di3_state;
int di4_state;

void setup(void)
{
  Serial.begin(9600);
  Serial.println("Starting setup");

  Bridge.begin();
  server.listenOnLocalhost();
  server.begin();
  server_startString = my_date();

 // delay(2000);
  
  Serial.print("Starting setup");

  // set the resolution to 12 bit (maybe 10 bit is good enough?)
  sensors1.begin();
  sensors1.setResolution(Thermometer1, 11);
  sensors1.setResolution(Thermometer2, 11);
  sensors1.setResolution(Thermometer3, 11);
  
  Serial.print("Set DIO states");
   
  pinMode(RELAY1, OUTPUT);
  pinMode(RELAY2, OUTPUT);
  pinMode(RELAY3, OUTPUT);
  pinMode(RELAY4, OUTPUT);
  pinMode(RELAY5, OUTPUT);
  pinMode(RELAY6, OUTPUT);
  pinMode(RELAY7, OUTPUT);  
  pinMode(RELAY8, OUTPUT);

  digitalWrite(RELAY1, HIGH);
  digitalWrite(RELAY2, HIGH);
  digitalWrite(RELAY3, HIGH);
  digitalWrite(RELAY4, HIGH);
  digitalWrite(RELAY5, HIGH);
  digitalWrite(RELAY6, HIGH);
  digitalWrite(RELAY7, HIGH);
  digitalWrite(RELAY8, HIGH);

  pinMode(DI1, INPUT);
  pinMode(DI2, INPUT);   
  pinMode(DI3, INPUT); 
  pinMode(DI4, INPUT);  
  digitalWrite(DI1, HIGH);   
  digitalWrite(DI2, HIGH);   
  digitalWrite(DI3, HIGH);   
  digitalWrite(DI4, HIGH);

  Serial.print("Setting timers");
  timer.setInterval(  200, read_dio2); // First timer doesn't start?  We don't need this anyway.
  timer.setInterval(   50, read_dio1);
  timer.setInterval(  200, read_server);
  
//  timer.setInterval(  1000, read_dio2); // First timer doesn't start? 
//  timer.setInterval(   500, read_dio1);
//  timer.setInterval(  1000, read_server);
  
  timer.setInterval(60000, read_temps);
  timer.setInterval(60000, write_xively);
 Serial.print("Done with setup\n");
  
}

void read_server(void) {
//    Serial.print('='); 
  YunClient client = server.accept();
  if (client) {
    serveClient(client);
  }
}

void serveClient (YunClient client) {
//    Serial.print(':'); 
    String command = client.readString();
    command.trim();        //kill whitespace
    Serial.println(command);
    if (command == "temperature") {
      String timeString = my_date();
      Serial.println(timeString);
      client.print("Current time on the Y�n: ");
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
    else if (command == "cover_open") {
      client.print("Cover open");
      cover_open();
    }
    else if (command == "cover_close") {
      client.print("Cover close");
      cover_close();
    } 
    else if (command == "cover_stop") {
      client.print("Cover stop");
      cover_relays_off();
    } 
    else if (command == "relay7_on") {
      digitalWrite(RELAY7, LOW);
      client.print("Relay 7 on");
    }
    else if (command == "relay7_off") {
      digitalWrite(RELAY7, HIGH);
      client.print("Relay 7 off");
    }
    else if (command == "relay8_on") {
      digitalWrite(RELAY8, LOW);
      client.print("Relay 8 on");
    }
    else if (command == "relay8_off") {
      digitalWrite(RELAY8, HIGH);
      client.print("Relay 8 off");
    } 
    else {
      Serial.println("Unknown command");
      client.print("<br>Unknown command");
    } 
    // Close connection and free resources.
    client.stop();
    server_hits++;
}

void read_dio1(void) { 

//  Serial.print('.'); 
  di1_state = digitalRead(DI1);
  di2_state = digitalRead(DI2);
  di3_state = digitalRead(DI3);
  di4_state = digitalRead(DI4);
//  Serial.print(di1_state); 
 
  if (di1_state == 0 or di2_state == 0) { 
    if (button_longpress) {
      if (cover_state == 1) { 
        cover_state = 2;
      }
      else if (cover_state == 2) {
        cover_state = 1;
      }
      button_longpress = 0;
                            // Timer has a bug, should get set in following cover call, but doesn't??
      cover_limit_timer = timer.setTimeout(1500, cover_limit_set_honor);
    }
    else if (!timer.isEnabled(button_longpress_timer)) {
      button_longpress_timer = timer.setTimeout(1000, button_longpress_set);
    }
  }

  if (di1_state == 0) {
    cover_open();
  }
  else if (di2_state == 0) {
    cover_close();
  }
  else if (di3_state == 0 and cover_limit_honor == 1) {
    cover_limit_honor = 0;
    cover_relays_off();
  }
  else {
    timer.deleteTimer(button_longpress_timer);
    button_longpress = 0;
  }
  
  // 3rd button for pulsing motor.
  if (di4_state == 0) {
    if (cover_state == 3 or cover_state == 4) {
      cover_relays_off();
      delay(300);  // 'debounce' the button, so we don't also execute the motor pulse code below
    }
    else if (cover_state < 5) {
      if (cover_state == 1) {
        cover_relays_open();
        cover_state = 5;
      }
      else if (cover_state == 2) {
        cover_relays_close();
        cover_state = 6;
      }
    }
  }
  else if (cover_state > 4) {
    cover_relays_off();
  }  
}

void read_dio2() { 
//    Serial.print('-'); 
  relay1_state = digitalRead(RELAY1);
  relay2_state = digitalRead(RELAY2);
  relay3_state = digitalRead(RELAY3);
  relay4_state = digitalRead(RELAY4);
  relay5_state = digitalRead(RELAY5);
  relay6_state = digitalRead(RELAY6);
  relay7_state = digitalRead(RELAY7);
  relay8_state = digitalRead(RELAY8);
  
  if (relay1_state == 1) { relay1_state = 0; } else { relay1_state = 1; }
  if (relay2_state == 1) { relay2_state = 0; } else { relay2_state = 1; }
  if (relay3_state == 1) { relay3_state = 0; } else { relay3_state = 1; }
  if (relay4_state == 1) { relay4_state = 0; } else { relay4_state = 1; }
  if (relay5_state == 1) { relay5_state = 0; } else { relay5_state = 1; }
  if (relay6_state == 1) { relay6_state = 0; } else { relay6_state = 1; }
  if (relay7_state == 1) { relay7_state = 0; } else { relay7_state = 1; }
  if (relay8_state == 1) { relay8_state = 0; } else { relay8_state = 1; }
}
    
void cover_open(void) {
  if (cover_state == 2 or cover_state == 0) {
    cover_relays_open();
    cover_limit_honor = 0;
    cover_limit_timer = timer.setTimeout(1500, cover_limit_set_honor);
//    cover_relay_timer = timer.setTimeout(4000, cover_relays_off);
    cover_relay_timer = timer.setTimeout(37000, cover_relays_off);
  }
  else if (cover_limit_honor == 1) {   // ignore 2nd button switch for a bit
    cover_relays_off();
  }
}

void cover_close(void) {
  if (cover_state == 1 or cover_state == 0) {
    cover_relays_close();
    cover_limit_honor = 0;
    cover_limit_timer = timer.setTimeout(1500, cover_limit_set_honor);
//    cover_relay_timer = timer.setTimeout(4000, cover_relays_off);
    cover_relay_timer = timer.setTimeout(56000, cover_relays_off);
  }
  else if (cover_limit_honor == 1) {
    cover_relays_off();
  }
}

void cover_limit_set_honor(void) {
  cover_limit_honor = 1;
}
void button_longpress_set(void) {
  button_longpress = 1;
}

void cover_relays_open(void) {
  Serial.print("Opening relays\n");
  cover_state = 3;
  digitalWrite(RELAY1, LOW);
  digitalWrite(RELAY2, LOW);
  digitalWrite(RELAY3, HIGH);
  digitalWrite(RELAY4, HIGH);
  digitalWrite(RELAY5, LOW);
  digitalWrite(RELAY6, LOW);
}

void cover_relays_close(void) {
  Serial.print("Closing relays\n");
  cover_state = 4;
  digitalWrite(RELAY1, LOW);
  digitalWrite(RELAY2, LOW);
  digitalWrite(RELAY3, LOW);
  digitalWrite(RELAY4, LOW);
  digitalWrite(RELAY5, HIGH);
  digitalWrite(RELAY6, HIGH);
} 

void cover_relays_off(void) {
  Serial.print("cover relays off\n");
  if (cover_state == 3 or cover_state == 5) { cover_state = 1; }
  if (cover_state == 4 or cover_state == 6) { cover_state = 2; }
  timer.deleteTimer(cover_relay_timer);
  digitalWrite(RELAY1, HIGH);
  digitalWrite(RELAY2, HIGH);
  digitalWrite(RELAY3, HIGH);
  digitalWrite(RELAY4, HIGH);
  digitalWrite(RELAY5, HIGH);
  digitalWrite(RELAY6, HIGH);
}


void read_temps(void) { 

  Serial.print("Reading temps ...");
    
                   // Skip if cover is moving, so we don't miss the limit switch 
  if (cover_state > 2) {
      return;
  }
  
  sensors1.requestTemperatures();
//Serial.print("done\n\r");
 
//float temp1f = DallasTemperature::toFahrenheit(sensors1.getTempC(Thermometer1));
  float temp1f = sensors1.getTempF(Thermometer1);
  float temp2f = sensors1.getTempF(Thermometer2);
  float temp3f = sensors1.getTempF(Thermometer3);
  
                                   // Sometimes we get -196.6 degree readings (noise on 1 wire bus?), so reread if needed
  int i = 4;
  while(i > 0){
    i--;
    if (temp1f < -50) {temp1f = sensors1.getTempF(Thermometer1);}
    if (temp2f < -50) {temp2f = sensors1.getTempF(Thermometer2);}
    if (temp3f < -50) {temp3f = sensors1.getTempF(Thermometer3);}
  }

//  if (temp1f < -50 or temp2f < -50 or temp3f < -50) { return; }

  sensor_data = "";
  sensor_data += "TempInlet,";
  sensor_data += temp1f;
  sensor_data += "\nTempPool,";
  sensor_data += temp2f;
  sensor_data += "\nTempAir,";
  sensor_data += temp3f;
  sensor_data += "\nTD_Inlet,";
  sensor_data += temp1f-temp2f;

//  Serial.print("Data:");
//  Serial.print(sensor_data);

}

void write_xively() { 
  String apiString = "X-ApiKey: ";
  apiString += APIKEY;
  String url = "https://api.xively.com/v2/feeds/";
  url += FEEDID;
  url += ".csv";

  Process xively;
  Serial.print("\nSending xively data... ");
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

