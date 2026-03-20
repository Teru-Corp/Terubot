#include "communication.h"
#include <Wire.h>

// We no longer need isMasterMode because the Pi is the Master.
// Both ESP32s act as "Listeners".

static constexpr size_t RX_BUFFER_SIZE = 64;
static volatile bool commandReady = false;
static volatile size_t lineLength = 0;
static char lineBuffer[RX_BUFFER_SIZE] = {0};
static char queuedCommand[RX_BUFFER_SIZE] = {0};

static void handleReceivedChar(char incoming) {
  if (incoming == '\0') {
    return;
  }

  if (incoming == '\r') {
    return;
  }

  if (incoming == '\n') {
    if (lineLength == 0) {
      return;
    }

    if (!commandReady) {
      size_t copyLen = lineLength;
      if (copyLen >= RX_BUFFER_SIZE) copyLen = RX_BUFFER_SIZE - 1;
      memcpy(queuedCommand, lineBuffer, copyLen);
      queuedCommand[copyLen] = '\0';
      commandReady = true;
    }

    lineLength = 0;
    lineBuffer[0] = '\0';
    return;
  }

  if ((unsigned char)incoming < 32) {
    return;
  }

  if (lineLength < (RX_BUFFER_SIZE - 1)) {
    lineBuffer[lineLength++] = incoming;
    lineBuffer[lineLength] = '\0';
  }
}

static void onI2CReceive(int bytesReceived) {
  while (bytesReceived-- > 0 && Wire.available()) {
    char incoming = (char)Wire.read();
    handleReceivedChar(incoming);
  }
}

static inline bool isValidCmd(String cmd) {
  return (cmd == "HAPPY" || cmd == "SAD" || cmd == "LEFT" || cmd == "RIGHT" || 
          cmd == "UP" || cmd == "DOWN" || cmd == "CENTER" || cmd == "BLINK" || 
          cmd == "YES" || cmd == "NO" || cmd == "NEUTRAL");
}

void commInit() {
  Wire.begin((uint8_t)I2C_SLAVE_ADDRESS, I2C_SDA_PIN, I2C_SCL_PIN, 100000);
  Wire.onReceive(onI2CReceive);

  lineLength = 0;
  commandReady = false;
  lineBuffer[0] = '\0';
  queuedCommand[0] = '\0';
}

String commGetCommand() {
  char localCmd[RX_BUFFER_SIZE] = {0};

  noInterrupts();
  if (!commandReady) {
    interrupts();
    return "";
  }

  size_t i = 0;
  while (i < (RX_BUFFER_SIZE - 1) && queuedCommand[i] != '\0') {
    localCmd[i] = queuedCommand[i];
    i++;
  }
  localCmd[i] = '\0';
  queuedCommand[0] = '\0';
  commandReady = false;
  interrupts();

  String cmd(localCmd);
  cmd.trim();
  cmd.toUpperCase();

  if (!isValidCmd(cmd)) {
    return "";
  }

  return cmd;
}

// This function is now empty because the Pi sends to both directly.
// We keep the function name so your main code doesn't break.
void commForwardToSlave(String cmd) {
  // Deprecated: Pi handles broadcasting now.
}