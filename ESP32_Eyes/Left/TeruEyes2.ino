#include "Expressions.h"
#include "behaviour.h"
#include "communication.h"

/* Waveshare ESP32-S3 Pins */
#define TFT_BL 40
#define SCK_PIN 10
#define MOSI_PIN 11
#define MISO_PIN -1
#define CS_PIN 9
#define DC_PIN 8
#define RST_PIN 12

// Logic Change: We no longer need IS_MASTER. 
// The Raspberry Pi handles the "Master" timing (like when to blink).

// Global Objects
Arduino_DataBus *bus = new Arduino_ESP32SPI(DC_PIN, CS_PIN, SCK_PIN, MOSI_PIN, MISO_PIN);
Arduino_GFX *tft = new Arduino_GC9A01(bus, RST_PIN, 0, true);
Arduino_Canvas *canvas = new Arduino_Canvas(240, 240, tft);

// Global State Variables
String currentCommand = "NEUTRAL";
float m = 0.0f;
float blinkSpeed = 5.0f;
bool isBlinking = false;
unsigned long lastUpdate = 0;
float morphProgress = 1.0f;

void processCommand(String cmd) {
  // Gaze commands
  if (cmd == "LEFT" || cmd == "RIGHT" || cmd == "UP" || cmd == "DOWN") {
    behaviourActivate(cmd);
    return;
  }

  // CENTER = Center gaze + Neutral expression
  if (cmd == "CENTER") {
    currentCommand = "NEUTRAL";  // Neutral expression
    morphProgress = 0.0f;
    behaviourActivate("CENTER");  // Center gaze
    return;
  }

  // BLINK = Blink command
  if (cmd == "BLINK") {
    isBlinking = true;
    blinkSpeed = 5.0f;
    m = 0.0f;
    return;
  }

  // HAPPY/SAD/YES/NO/NEUTRAL = Expression commands
  currentCommand = cmd;
  morphProgress = 0.0f;
  if (currentCommand == "SAD") sadActivate();
  behaviourActivate("CENTER");
}

void setup() {
  // FIX: commInit no longer takes a boolean parameter
  commInit(); 

  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  tft->begin();
  canvas->begin();

  randomSeed((uint32_t)esp_random());

  lastUpdate = millis();

  // Start with neutral centered gaze
  behaviourActivate("CENTER");
  currentCommand = "NEUTRAL";
}

void loop() {
  unsigned long now = millis();
  float dt = (now - lastUpdate) / 1000.0f;
  lastUpdate = now;

  if (dt < 0.0f) dt = 0.0f;
  if (dt > 0.05f) dt = 0.05f; 

  // 1) SERIAL INPUT - Check for incoming commands from Raspberry Pi
  String cmd = commGetCommand();
  if (cmd != "") {
    processCommand(cmd);
  }

  // 2) ANIMATION - Blink and gaze behavior (controlled by commands)
  // Only update blink animation if currently blinking
  if (isBlinking) {
    unsigned long tempNextBlinkTime = 0;
    updateBlink(m, isBlinking, blinkSpeed, tempNextBlinkTime, dt);
  } else {
    m = 0.0f;  // Keep eyes open when not blinking
  }

  // Update gaze behavior (responds to LEFT/RIGHT/UP/DOWN/CENTER commands and idle wandering)
  behaviourUpdate(dt);
  float gazeX = behaviourGetGazeX();
  float gazeY = behaviourGetGazeY();

  if (currentCommand == "SAD") {
    sadUpdate(dt);
  }

  if (morphProgress < 1.0f) {
    morphProgress += 2.0f * dt;
    if (morphProgress > 1.0f) morphProgress = 1.0f;                                                                                                                                                                                                                                                                                                                                                

  // 3) DRAW - Render to screen
  canvas->fillScreen(COL_BG);

  float lidAmount = m;
  if (currentCommand == "SAD") {
    lidAmount = 0.5f + (m * 0.3f); 
  }

  // Draw base eye (only if not in sad mode, since sad mode uses custom lid)
  if (currentCommand != "SAD") {
    drawBaseEye(120.0f, 120.0f, lidAmount, gazeX, gazeY, -1);
  } else {
    // For sad expression, draw eye without lid first, then add tilted sad lid
    drawBaseEye(120.0f, 120.0f, 0.0f, gazeX, gazeY, -1);  // Draw with open eyes
    drawSadLid(120.0f, 120.0f, lidAmount, -1);  // Draw tilted sad lid instead
  }

  if (currentCommand == "SAD") {
    drawSadExtras(120.0f, 120.0f, 120.0f, -1);
  }
  if (currentCommand == "HAPPY") {
    drawHappyExtras(120.0f, 120.0f, morphProgress, -1);
  }

  canvas->flush();
}