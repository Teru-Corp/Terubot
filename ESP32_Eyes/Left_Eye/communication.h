#pragma once

#include <Arduino.h>

// Communication pins (Keep these defined, though they aren't used for USB)
#define RX2 36
#define TX2 35

// Initialize communication (USB Serial only)
// REMOVED: bool isMaster
void commInit();

// Check for incoming commands from the Pi and return the character
char commGetCommand();

// This is kept for compatibility so TeruEyes.ino doesn't crash, 
// but it won't do anything in USB mode.
void commForwardToSlave(char cmd); 