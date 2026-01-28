#include <Arduino.h>
#include <Adafruit_PWMServoDriver.h>
#include "Motion.h"
#include "Tracking.h"
#include "Pins.h"


// These are defined in TeruMotors.ino, we "import" them here
extern int R_CENTER, L_CENTER, PAN_CENTER;
extern int MIN_ANG, MAX_ANG;
extern int PULSE_MIN, PULSE_MAX;

extern float currentNod, currentTilt, currentPan;


extern Adafruit_PWMServoDriver pwm;

void writeAngle(int ch, int angle) {
  angle = constrain(angle, MIN_ANG, MAX_ANG);
  int pulse = map(angle, 0, 180, PULSE_MIN, PULSE_MAX);
  pwm.setPWM(ch, 0, pulse);
}

static void writeCurrentPoseWithTrackingOverlay() {
  // Fade tracking if updates stop
  updateTrackingFade();

  int rBase = R_CENTER + (DIR_R * (currentNod - 90));
  int lBase = L_CENTER + (DIR_L * (currentNod - 90));

  float tiltOut = currentTilt + trackTiltOff;
  float panOut  = currentPan  + trackPanOff;

  writeAngle(TILT_R_CH, rBase + (DIR_R * tiltOut));
  writeAngle(TILT_L_CH, lBase - (DIR_L * tiltOut));
  writeAngle(PAN_CH, (int)panOut);
}

void moveTo(float targetNod, float targetTilt, float targetPan, float speed) {
  while (abs(currentNod - targetNod) > 0.2 || abs(currentTilt - targetTilt) > 0.2 || abs(currentPan - targetPan) > 0.2) {

    // Interrupt if a manual command arrives.
    // But if it's tracking ('T'), parse it and KEEP moving (so tracking doesn't freeze motion).
    if (Serial.available() > 0) {
      int c = Serial.peek();
      if (c == 'T') {
        Serial.read();        // consume 'T'
        parseTrackingLine();  // reads ",pan,tilt\n" and updates offsets
        // do NOT return
      } else {
        return;               // interrupt for H/S/Y/N/Q/etc.
      }
    }

    float stepNod = (targetNod - currentNod) * speed;
    float stepTilt = (targetTilt - currentTilt) * speed;
    float stepPan = (targetPan - currentPan) * speed;

    currentNod  += (abs(stepNod) < 0.05 && abs(stepNod) > 0) ? (stepNod > 0 ? 0.05 : -0.05) : stepNod;
    currentTilt += (abs(stepTilt) < 0.05 && abs(stepTilt) > 0) ? (stepTilt > 0 ? 0.05 : -0.05) : stepTilt;
    currentPan  += (abs(stepPan) < 0.05 && abs(stepPan) > 0) ? (stepPan > 0 ? 0.05 : -0.05) : stepPan;

    writeCurrentPoseWithTrackingOverlay();

    delay(15);
  }
}


// ----------------- PET BEHAVIORS -----------------

void idleLookAround() {
  Serial.println("Action: Looking around...");

  float rNod = random(85, 115);
  float rPan = random(60, 120);
  float rTilt = random(-15, 15);
  float rSpeed = random(40, 80) / 1000.0;

  moveTo(rNod, rTilt, rPan, rSpeed);
}

void idleTwitch() {
  Serial.println("Action: Twitch");
  float tPan = currentPan + random(-10, 10);
  float tNod = currentNod + random(-5, 5);
  moveTo(tNod, currentTilt, tPan, 0.15);
}

// ----------------- EXPRESSIONS -----------------
void expressHappy() { for(int i=0;i<2;i++){ moveTo(85, 15, 90, 0.12); moveTo(85, -15, 90, 0.12); } moveTo(90, 0, 90, 0.1); }
void expressSad()   { moveTo(125, 0, 90, 0.03); }
void expressYes()   { for(int i=0;i<3;i++){ moveTo(80, 0, 90, 0.08); moveTo(100, 0, 90, 0.08); } moveTo(90, 0, 90, 0.08); }
void expressNo()    { for(int i=0;i<2;i++){ moveTo(90, 0, 110, 0.2); moveTo(90, 0, 70, 0.2); } moveTo(90, 0, 90, 0.1); }
void expressQuest() { moveTo(95, -20, 110, 0.06); }

// ----------------- DIRECTIONAL MOVEMENTS -----------------
void moveUp()    { moveTo(75, 0, currentPan, 0.08); }
void moveDown()  { moveTo(115, 0, currentPan, 0.08); }
void moveLeft()  { moveTo(currentNod, 0, 110, 0.08); }
void moveRight() { moveTo(currentNod, 0, 70, 0.08); }

// ----------------- COMMAND ROUTER -----------------
void handleCommand(char cmd) {
  if (cmd == 'H') expressHappy();
  else if (cmd == 'S') expressSad();
  else if (cmd == 'Y') expressYes();
  else if (cmd == 'N') expressNo();
  else if (cmd == 'Q') expressQuest();
  else if (cmd == 'C') moveTo(90, 0, 90, 0.08);
  else if (cmd == 'U') moveUp();
  else if (cmd == 'D') moveDown();
  else if (cmd == 'L') moveLeft();
  else if (cmd == 'R') moveRight();
}
