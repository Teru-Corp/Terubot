#pragma once

// gaze output is normalized: -1.0 (left/up) to +1.0 (right/down)
void behaviourActivate(char cmd);
void behaviourUpdate(float dt);
float behaviourGetGazeX();
float behaviourGetGazeY();
