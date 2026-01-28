#pragma once

// Expose the functions your main loop uses
void handleCommand(char cmd);

void writeAngle(int ch, int angle);
void moveTo(float targetNod, float targetTilt, float targetPan, float speed);

void idleLookAround();
void idleTwitch();

// Expressions
void expressHappy();
void expressSad();
void expressYes();
void expressNo();
void expressQuest();

// Directional moves
void moveUp();
void moveDown();
void moveLeft();
void moveRight();
