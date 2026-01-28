#pragma once
#include <Arduino.h>

// Shared tracking offsets (read by Motion.cpp)
extern float trackPanOff;
extern float trackTiltOff;

// Parse "T,pan,tilt\n" after the 'T' has been read
void parseTrackingLine();

// Apply tracking overlay immediately (used in loop)
void applyPoseWithTracking();

// Fade logic (used by Motion.cpp too)
void updateTrackingFade();
