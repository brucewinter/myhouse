#if 1 // Change to 1 to enable this code (must enable ONE user*.cpp only!)
// CORRESPONDING LINE IN HeatSensor.cpp MUST ALSO BE ENABLED!

// 04/19/2020 
//   Modified to add servo, demo at https://youtu.be/4ESjNbYZQHg
//   Original from: https://raw.githubusercontent.com/adafruit/Adafruit_Learning_System_Guides/master/M4_Eyes/user_watch.cpp

#include "globals.h"
#include "heatSensor.h"

#include <Servo.h>
Servo myservo;
#define SERVO_LOW      600
#define SERVO_HIGH    2400
#define SERVO_MID     1500
#define SERVO_PIN        3

// For heat sensing
HeatSensor heatSensor;

// This file provides a crude way to "drop in" user code to the eyes,
// allowing concurrent operations without having to maintain a bunch of
// special derivatives of the eye code (which is still undergoing a lot
// of development). Just replace the source code contents of THIS TAB ONLY,
// compile and upload to board. Shouldn't need to modify other eye code.

// User globals can go here, recommend declaring as static, e.g.:
// static int foo = 42;

// Called once near the end of the setup() function. If your code requires
// a lot of time to initialize, make periodic calls to yield() to keep the
// USB mass storage filesystem alive.
void user_setup(void) {
  showSplashScreen = false;
  moveEyesRandomly = false;
  heatSensor.setup();
}

// Called periodically during eye animation. This is invoked in the
// interval before starting drawing on the last eye (left eye on MONSTER
// M4SK, sole eye on HalloWing M0) so it won't exacerbate visible tearing
// in eye rendering. This is also SPI "quiet time" on the MONSTER M4SK so
// it's OK to do I2C or other communication across the bridge.

int servo1 = (int)SERVO_MID;

void user_loop(void) {
  // Estimate the focus position.
  heatSensor.find_focus();
  
  // Set values for the new X and Y.
  eyeTargetX = heatSensor.x;
  eyeTargetY = -heatSensor.y;

  int servo2 = 100 * heatSensor.x;
  
  if (servo2 < 15 && servo2 > -15) {
    myservo.detach();
  }
  else {
// heuristicaly derived, fastest possible.  higher leads to oscilations
// also depends on eye, as the frame rate is different for different eyes
//  servo1 += servo2 * 1.25; 
    servo1 += servo2 * 0.75;
    if (servo1 > SERVO_HIGH) {
      servo1 = SERVO_HIGH;
    }
    else if (servo1 < SERVO_LOW) {
      servo1 = SERVO_LOW;
    }
    else {
      if(!myservo.attached()) {
	myservo.attach(SERVO_PIN);
      }
      myservo.writeMicroseconds(servo1);
//    delay(10);
    }
  }

#define DEBUG1 0
#if DEBUG1 == 1
  Serial.print("db 1a: ");
  Serial.print(servo2);
  Serial.print(' ');
  Serial.print(eyeTargetY);
  Serial.print(' ');
  Serial.print(servo1);
  Serial.println();
#endif

}

#endif // 0

