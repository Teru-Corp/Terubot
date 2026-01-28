#include "communication.h"

// We no longer need isMasterMode because the Pi is the Master.
// Both ESP32s act as "Listeners".

static inline bool isValidCmd(char c) {
  return (c == 'H' || c == 'S' || c == 'L' || c == 'R' || c == 'U' || c == 'D' || c == 'C' || c == 'B');
}

void commInit() {
  // 115200 must match your Python script BAUD_RATE
  Serial.begin(115200);
  delay(500);  // Give Serial time to initialize

  // Wait for Serial to initialize
  unsigned long start = millis();
  while (!Serial && millis() - start < 2000) {
    delay(10);
  }

  Serial.println("\n\n===== Display ESP32 Ready =====");
  Serial.println("Listening for commands from Serial Monitor or Raspberry Pi...");
  Serial.println("Valid commands: H=happy, S=sad, C=center/neutral, L=left, R=right, U=up, D=down, B=blink");
  Serial.println("Baud Rate: 115200");
  Serial.println("==============================\n");
}

char commGetCommand() {
  char cmd = '\0';
  
  // Both ESP32s now check the main Serial (USB)
  if (Serial.available()) {
    char incoming = Serial.read();
    
    // Debug: Print raw byte received
    Serial.print("[RX] Raw byte: ");
    Serial.print((int)incoming);
    Serial.print(" ('");
    Serial.print(incoming);
    Serial.println("')");
    
    // Ignore line endings and spaces
    if (incoming == '\n' || incoming == '\r' || incoming == ' ') {
      Serial.println("[RX] Ignoring whitespace");
      return '\0';
    }
    
    cmd = (char)toupper((unsigned char)incoming);
    
    if (!isValidCmd(cmd)) {
      Serial.print("[RX] Invalid command: ");
      Serial.println(cmd);
      return '\0';
    }

    // Confirm valid command
    Serial.print("[ACK] Executing: ");
    Serial.println(cmd);
  }
  
  return cmd;
}

// This function is now empty because the Pi sends to both directly.
// We keep the function name so your main code doesn't break.
void commForwardToSlave(char cmd) {
  // Deprecated: Pi handles broadcasting now.
}