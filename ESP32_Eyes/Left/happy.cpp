#include "Expressions.h"

// Static variables to track happy expression timing
static unsigned long happyStartTime = 0;
static bool happyActive = false;

// Helper function to draw a FILLED star at position (cx, cy) with given size
void drawStar(float cx, float cy, float size, uint16_t color) {
  // Draw a filled star using triangles
  float outerRadius = size;
  float innerRadius = size * 0.4f;
  
  // Create 5 outer points and 5 inner points
  float points[10][2];
  for (int i = 0; i < 10; i++) {
    float angle = (i * 36) * 3.14159f / 180.0f;
    float radius = (i % 2 == 0) ? outerRadius : innerRadius;
    points[i][0] = cx + radius * cosf(angle);
    points[i][1] = cy + radius * sinf(angle);
  }
  
  // Fill star with triangles from center to each point
  for (int i = 0; i < 10; i++) {
    int next = (i + 1) % 10;
    canvas->fillTriangle(
      (int)cx, (int)cy,
      (int)points[i][0], (int)points[i][1],
      (int)points[next][0], (int)points[next][1],
      color
    );
  }
}

void drawHappyExtras(float cx, float cy, float progress, int sideSign) {
  // Track when happy expression started for continuous blinking
  if (progress > 0.1f && !happyActive) {
    happyActive = true;
    happyStartTime = millis();
  }
  
  // Use time-based animation for continuous blinking
  unsigned long elapsedTime = millis() - happyStartTime;
  float timeProgress = (elapsedTime % 1000) / 1000.0f;  // Loops every 1 second
  
  // Combine morphing progress (for initial animation) with continuous time pulse
  float animationValue = progress;
  if (progress >= 0.8f) {
    // Once morphing is done, use continuous time-based pulse
    animationValue = 0.8f + (sinf(timeProgress * 3.14159f * 2.0f) * 0.2f);
  }
  
  if (animationValue > 0.1f) {
    float poundEffect = sinf(animationValue * 3.14159f);
    
    // Star 1 - Upper left (VERY BIG to small variation)
    float size1 = 8.0f + (poundEffect * 12.0f);
    drawStar(cx + 70.0f, cy - 70.0f, size1, COL_WHITE);
    
    // Star 2 - Upper right (offset phase for alternating blink)
    float offsetProgress = fmodf(timeProgress + 0.25f, 1.0f);
    float poundEffect2 = sinf(offsetProgress * 3.14159f);
    float size2 = 7.0f + (poundEffect2 * 11.0f);
    drawStar(cx - 70.0f, cy - 65.0f, size2, COL_WHITE);
    
    // Star 3 - Top center (offset phase)
    float offsetProgress3 = fmodf(timeProgress + 0.5f, 1.0f);
    float poundEffect3 = sinf(offsetProgress3 * 3.14159f);
    float size3 = 6.0f + (poundEffect3 * 10.0f);
    drawStar(cx, cy - 85.0f, size3, COL_WHITE);
    
    // Star 4 - Lower left (offset phase)
    float offsetProgress4 = fmodf(timeProgress + 0.75f, 1.0f);
    float poundEffect4 = sinf(offsetProgress4 * 3.14159f);
    float size4 = 7.0f + (poundEffect4 * 10.0f);
    drawStar(cx + 50.0f, cy + 20.0f, size4, COL_WHITE);
    
    // Star 5 - Lower right (offset phase) - bonus star for more sparkle
    float offsetProgress5 = fmodf(timeProgress + 0.35f, 1.0f);
    float poundEffect5 = sinf(offsetProgress5 * 3.14159f);
    float size5 = 6.0f + (poundEffect5 * 9.0f);
    drawStar(cx - 55.0f, cy + 15.0f, size5, COL_WHITE);
  }
}