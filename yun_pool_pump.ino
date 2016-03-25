
// Read air sensor data and post to Xively 
// Server example from:  Info at: http://arduino.cc/en/Tutorial/TemperatureWebPanel



#include <Bridge.h>
#include <YunServer.h>
#include <YunClient.h>
#include <Process.h>
#include "passwords.h"
#include "DHT.h"
#include <Wire.h>
#include <Digital_Light_TSL2561.h>

#define RELAY1 4
#define RELAY2 5
#define RELAY3 6
#define RELAY4 7

#define PIN_DUST 8 
#define PIN_DHT A0 
#define PIN_VOL A2 
#define VREF 4.95
#define DHTTYPE DHT22   // DHT 22  (AM2302)

DHT dht(PIN_DHT, DHTTYPE);

const unsigned long interval_ms = 60000; 
unsigned       long time_ms = 0;  
unsigned       long dust_duration_total = 0;
String sensor_data = "";
String other_data = "";

YunServer server;
String server_startString;
long server_hits = 0;

void setup() {
  Serial.begin(9600);
  Serial.println("Send air sensor data to Xively");
  Bridge.begin();
  server.listenOnLocalhost();
  server.begin();
  dht.begin();               // Humidty and Temp sensor
  pinMode(PIN_DUST, INPUT);  // Dust sensor
  pinMode(RELAY1, OUTPUT);
  pinMode(RELAY2, OUTPUT);
  pinMode(RELAY3, OUTPUT);
  pinMode(RELAY4, OUTPUT);
  digitalWrite(RELAY1, HIGH);
  digitalWrite(RELAY2, HIGH);
  digitalWrite(RELAY3, HIGH);
  digitalWrite(RELAY4, HIGH);
  Wire.begin();              // Light sensor
  TSL2561.init();            // Light sensor
  time_ms = millis();
  server_startString = my_date();
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
      String timeString = my_date();
      Serial.println(timeString);

      client.print("Current time on the Yún: ");
      client.println(timeString);
      client.print("<br>Sensor data: ");
      client.print(sensor_data);
      client.print("<br>Other data: ");
      client.print(other_data);
      client.print("<br>This sketch has been running since ");
      client.print(server_startString);
      client.print("<br>Hits so far: ");
      client.print(server_hits);
    }
    else if (command == "reset") {  
       client.print("Resetting mpu");
//     resetFunc();
       Process reset_mcu;
       reset_mcu.runShellCommand("/usr/bin/reset-mcu");
       client.print("<br>Reset done");
    }
    else if (command == "speed1") {
      digitalWrite(RELAY1, HIGH);
      digitalWrite(RELAY2, HIGH);
      digitalWrite(RELAY3, HIGH);
      client.print("speed set to 1");
    }
    else if (command == "speed2") {
      digitalWrite(RELAY1, LOW);
      digitalWrite(RELAY2, HIGH);
      digitalWrite(RELAY3, HIGH);
      client.print("speed set to 2");
    }
    else if (command == "speed3") {
      digitalWrite(RELAY1, HIGH);
      digitalWrite(RELAY2, LOW);
      digitalWrite(RELAY3, HIGH);
      client.print("speed set to 3");
    }
    else if (command == "speed4") {
      digitalWrite(RELAY1, LOW);
      digitalWrite(RELAY2, LOW);
      digitalWrite(RELAY3, HIGH);
      client.print("speed set to 4");
    }
    else if (command == "speed5") {
      digitalWrite(RELAY1, HIGH);
      digitalWrite(RELAY2, HIGH);
      digitalWrite(RELAY3, LOW);
      client.print("speed set to 5");
    }
    else if (command == "speed6") {
      digitalWrite(RELAY1, LOW);
      digitalWrite(RELAY2, HIGH);
      digitalWrite(RELAY3, LOW);
      client.print("speed set to 6");
    }
    else if (command == "speed7") {
      digitalWrite(RELAY1, HIGH);
      digitalWrite(RELAY2, LOW);
      digitalWrite(RELAY3, LOW);
      client.print("speed set to 7");
    }
    else if (command == "speed8") {
      digitalWrite(RELAY1, LOW);
      digitalWrite(RELAY2, LOW);
      digitalWrite(RELAY3, LOW);
      client.print("speed set to 8");
    }
    else if (command == "pump_on") {
      digitalWrite(RELAY4, LOW);
      client.print("pump set to on");
    }
    else if (command == "pump_off") {
      digitalWrite(RELAY4, HIGH);
      client.print("pump set to off");
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
  float h = dht.readHumidity();
  float t = Fahrenheit(dht.readTemperature());
    
  // Measure air density
  int sensorValue = analogRead(PIN_VOL);
  float vol=(float)sensorValue/1023*VREF;

  // Measure light
  Serial.print("getting light ... ");
  TSL2561.getLux();
  int l = TSL2561.calculateLux(0,0,1);
  Serial.print("The Light value is: ");
  Serial.println(l);
 
  // Send data
  int yunnum = 1;
  sensor_data = "";
  sensor_data += "\nTemperature"; sensor_data += yunnum;  sensor_data += ",";
  sensor_data += t;
  sensor_data += "\nHumidity";   sensor_data += yunnum;  sensor_data += ",";
  sensor_data += h;
  sensor_data += "\nDust";       sensor_data += yunnum;  sensor_data += ",";
  sensor_data += dust;
  sensor_data += "\nLight";      sensor_data += yunnum;  sensor_data += ",";
  sensor_data += l;
  Serial.print(sensor_data); 
  // If NotANumber, something went wrong
  if (isnan(t) || isnan(h) || isnan(dust) || isnan(vol)) {
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

  other_data = "xively results:";
  while (xively.available()>0) {
    char c = xively.read();
    Serial.write(c);
    other_data += c;
  }
  other_data += ".";
}

//Celsius to Fahrenheit conversion
double Fahrenheit(double celsius) {
  return 1.8 * celsius + 32;
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




