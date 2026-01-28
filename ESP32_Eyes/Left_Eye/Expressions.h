#ifndef EXPRESSIONS_H
#define EXPRESSIONS_H

#include <Arduino_GFX_Library.h>
#include <math.h>

extern Arduino_Canvas *canvas;

/* Shared Colors */
#define COL_BG       0xFFFF 
#define COL_EYE_BG   0xB6BF
#define COL_IRIS     0x1155 
#define COL_WHITE    0xFFFF 
#define COL_LID      0xFFFF 
#define COL_LID_EDGE 0xFFFF

// Updated prototypes
void drawBaseEye(float cx, float cy, float m, float gazeX, float gazeY);
void updateBlink(float &m, bool &isBlinking, float &blinkSpeed, unsigned long &nextBlinkTime, float dt);

// SAD logic functions
void sadActivate();
void sadUpdate(float dt);
void drawSadExtras(float cx, float cy, float outer_r, int sideSign);
void drawSadLid(float cx, float cy, float lidAmount);

// HAPPY logic
void drawHappyExtras(float cx, float cy, float progress);

#endif