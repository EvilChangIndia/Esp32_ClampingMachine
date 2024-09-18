# Clamping and Rotation Robot

## Description
Welcome to my Object Clamping and Rotation Robot project! This repository contains the code and hardware specifications for a versatile robotic system designed specifically for clamping and rotating microphones on an assembly line. The robot runs on esp32 and takes commands over CAN bus. A UI is also include, which can be run on a RPi 3b.

## Table of Contents
- Hardware Setup
- Installation
- Usage

## Hardware Setup
- Controller: Esp32 Nodemcu
- UI: 7inch touch display + RPi 3B. Foot-pedal for easier control.
- Rotation Mechanism: Igus harmonic drive + Nema 17.
- Clamping Mechanism: Pneumatic linear actuator (solenoid valve + 5V relay)
  
## Installation
1. Clone the repository into your PC:
   ```
   git clone https://github.com/EvilChangIndia/Esp32_ClampingMachine
   ```
2. Use arduino IDE to upload the **clamp_esp_sm_v4.ino** firmware into the ESP32. The file is inside the folder with the same name.
3. Copy the "clamp_pi" folder into the raspberry pi home folder. 


## Usage
To operate the Object Clamping and Rotation Robot, follow these steps:

1. Run the Application:

- On your Raspberry Pi, navigate to the project directory and run the **clampUI.py** Python file:
  ```
  python3 clampUI.py
  ```
2. Control Methods:
The bot can be controlled entirely through either of the options.
- **Foot Pedal**:
  - **Long Press**: To clamp or unclamp the microphone, press and hold the foot pedal.
  - **Short Presses**: Briefly pressing the foot pedal will trigger rotation of the microphone.
- **Touch Screen UI**:
  - Use the touch screen interface to control both clamping and rotation. The UI provides buttons for easy access to these functions.

3. **Optional**
   Shell Setup:
   If you want the clampUI.py to start automatically when your Raspberry Pi boots up, you can set up a shell script:
   -  Create a shell script (e.g., start_clamp.sh) with the following content:
      ```
      #!/bin/bash
      python3 /path/to/your/clampUI.py
      ```
   - Make the script executable:
     ```
     chmod +x start_clamp.sh
     ```
   - Add the script to your crontab to run at startup:
     ```
     crontab -e#
     ```
   - Add the following line to the end of the file:
     ```
     @reboot /path/to/your/start_clamp.sh
     ```
   

This setup allows for easy and efficient control of the robot, streamlining operations on your assembly line. Enjoy using your Object Clamping and Rotation Robot!

