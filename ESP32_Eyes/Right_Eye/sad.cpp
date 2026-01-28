#include "Expressions.h"

static float tear_size = 0.0f;
static const float tear_max = 1.2f;
static const float tear_speed = 0.35f;
static bool isSadActive = false;

void sadActivate() {
    tear_size = 0.0f;
    isSadActive = true;
}

void sadUpdate(float dt) {
    if (tear_size < tear_max) tear_size += tear_speed * dt;
    if (tear_size > tear_max) tear_size = tear_max;
}

void fillEllipse(Arduino_Canvas* c, int cx, int cy, int rx, int ry, uint16_t col) {
    if (rx <= 0 || ry <= 0) return;
    for (int y = -ry; y <= ry; y++) {
        float yy = (float)y / (float)ry;
        float inside = 1.0f - yy * yy;
        if (inside < 0.0f) continue;
        int x = (int)(rx * sqrtf(inside));
        c->drawFastHLine(cx - x, cy + y, 2 * x + 1, col);
    }
}

// Draw a tilted, curved sad lid
void drawSadLid(float cx, float cy, float lidAmount) {
    float R = 120.0f;
    
    // Create a tilted, downward curve for sad expression
    // Left side droops more than right side, positioned higher
    for (int x = -120; x <= 120; x++) {
        float xf = (float)x;
        if (xf * xf <= R * R) {
            float semiY = sqrt(R * R - xf * xf);
            
            // Create stronger tilt - right side (positive x) droops MORE
            float tiltFactor = (xf / 120.0f) * -35.0f;  // Negated to mirror the tilt direction
            
            // Create inverted sad curve - curves upward
            float sadCurve = (1.0f - lidAmount) * (semiY * 0.5f);
            
            // Move lid higher by reducing startY offset
            float arcY = (2.0f * lidAmount - 1.0f) * semiY + sadCurve - tiltFactor - 20.0f;
            int startY = (int)(cy - semiY + 0.5f);
            int endY = (int)(cy + arcY + 0.5f);

            if (endY > startY) {
                canvas->drawFastVLine((int)cx + x, startY, endY - startY, COL_LID);
                canvas->drawPixel((int)cx + x, endY, COL_LID_EDGE);
                canvas->drawPixel((int)cx + x, endY - 1, COL_LID_EDGE);
            }
        }
    }
}

void drawSadExtras(float cx, float cy, float outer_r, int sideSign) {

    // 🌊 WATER-BLUE TEAR COLOR (close to #3FA7D6)
    const uint16_t DROP_COLOR = 0x5E9F;  

    int drop_x = (int)cx;
    int drop_y = (int)(cy + outer_r);

    // 🔽 BIGGER TEAR
    float w = 90.0f * tear_size;
    float h = 50.0f * tear_size;

    if (w <= 1.0f || h <= 1.0f) return;

    int rx = (int)(w * 0.5f);
    int ry = (int)(h * 0.5f);

    drop_x += sideSign * 8;

    fillEllipse(canvas, drop_x, drop_y, rx, ry, DROP_COLOR);
}
