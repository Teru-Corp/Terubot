#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

#include "Motion.h"
#include "Tracking.h"
#include "Pins.h"

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// ----------------- SETTINGS -----------------
#define SERVO_FREQ 50

// These must exist (Motion.cpp uses them via extern)
int R_CENTER = 90, L_CENTER = 90, PAN_CENTER = 90;
int MIN_ANG = 10, MAX_ANG = 170;
int PULSE_MIN = 150, PULSE_MAX = 600;

float currentNod = 90.0, currentTilt = 0.0, currentPan = 90.0;
unsigned long lastActionTime = 0;
unsigned long nextActionDelay = 2000;

void setup() {
  Serial.begin(115200);
  Wire.begin(5, 6);

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);

  randomSeed(analogRead(0));

  moveTo(90, 0, 90, 0.05); // Start centered
}

void loop() {
  // 1) LISTEN FOR SERIAL (tracking OR commands)
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    // Tracking message: "T,pan,tilt\n"
    if (cmd == 'T') {
      parseTrackingLine();     // reads the rest of the line until '\n'
      // NOTE: do NOT reset lastActionTime here if you want idle to keep happening
    } 
    else {
      // Clear extra chars like \n \r so commands don't double-trigger
      while (Serial.available() > 0) Serial.read();

      handleCommand(cmd);      // H/S/Y/N/Q/C/U/D/L/R
      lastActionTime = millis();
    }
  }

  // 2) Apply tracking overlay continuously (so it follows even while waiting)
  applyPoseWithTracking();

  // 3) IDLE LOGIC
  if (millis() - lastActionTime > nextActionDelay) {
    int choice = random(0, 10);
    if (choice < 7) idleLookAround();
    else idleTwitch();

    lastActionTime = millis();
    nextActionDelay = random(1500, 4000);
  }
}
