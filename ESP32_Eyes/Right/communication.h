#pragma once

#include <Arduino.h>

// I2C slave settings (must match Raspberry Pi target address/pins)
// Waveshare round display IMU I2C lines: SDA=6, SCL=7
#define I2C_SDA_PIN 6
#define I2C_SCL_PIN 7
#define I2C_SLAVE_ADDRESS 0x10 //0x11 FOR THE OTHER ONE

// Initialize communication using I2C slave mode
void commInit();

// Check for incoming commands from the Pi and return the command string
String commGetCommand();

// This is kept for compatibility so TeruEyes.ino doesn't crash, 
// but it won't do anything in USB mode.
void commForwardToSlave(String cmd); 