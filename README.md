# Terubot
This repository contains the hardware and control code for TeruBot. It includes ESP32 firmware for expressive eye displays and servo motor control, as well as Raspberry Pi scripts for communication and behavior coordination between modules.



## ⚙️ Hardware Architecture

TeruBot is built on a distributed system:

- **Raspberry Pi 5** running a local language model (Qwen 2.5 – 1.5B) for voice processing and emotional keyword detection. 
- **Eye system**: two *Waveshare 1.28″ ESP32-S3 Round Display* boards generating procedural eye animations.
- **Motor system**: one *Seeed Studio XIAO ESP32-S3* controlling servo motors for head movements.
- **Logitech C270 webcam** for presence detection and voice capture.
- Custom 3D-printed mechanical parts (STL files).

The Raspberry Pi communicates with ESP32 boards via serial connections to synchronize visual and physical expressions.

## 🎯 Project Goal

TeruBot explores how a social robot can make emotions visible and shareable in a playful and non-intrusive way, fostering empathy and collective well-being in small communities.

## 🛠️ Usage

1. Flash the firmware in `ESP32_Eyes` and `ESP32_HeadMotors`.
2. Run the control scripts in `RaspPi5_Brain`.
3. Print and assemble the robot using STL files from `Terubot_parts`.



