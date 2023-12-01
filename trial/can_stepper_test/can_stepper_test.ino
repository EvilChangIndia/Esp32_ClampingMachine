
//for CAN bus
#include <CanBusMCP2515_asukiaaa.h>
#ifndef PIN_CS
#define PIN_CS 5
#endif
#ifndef PIN_INT
#define PIN_INT 17
#endif
#ifndef PIN_RST
#define PIN_RST -1
#endif
static const auto QUARTZ_FREQUENCY =
    CanBusMCP2515_asukiaaa::QuartzFrequency::MHz8;
static const auto BITRATE = CanBusMCP2515_asukiaaa::BitRate::Kbps125;
#ifndef CAN_ID
#define CAN_ID 3000
#endif

const int dirPin = 26;
const int stepPin = 25;
const int enPin = 27;
const int endStop = 33;
const int endStopVcc = 32;



//for stepper
#include <AccelStepper.h>
#define motorInterfaceType 1
//some custom settings
const int posPerRev = 1600;          //for 1/8 micro stepping
//experiment for other steps
const int gearRatio = 38;           //of the wormgear
int maxVelocity = posPerRev*12;    //make it multiples of posPerRev
int acceleration = maxVelocity/2;  //worked better this way. Will affect postioning accuracy
int jogVelocity = 500;
int revolutions = 1;
int steps=0;
int home=0;
int angle=0;
int angleFlag=0;
int endStopRead=0;
int calibrated=0;
int microCalib=0;
int sweepRange=50000;
//make instances
AccelStepper myStepper(motorInterfaceType, stepPin, dirPin);
CanBusMCP2515_asukiaaa::Driver can(PIN_CS, PIN_INT, PIN_RST);

void setup() {
  //for stepper
  pinMode(enPin, OUTPUT);
  myStepper.setMaxSpeed(maxVelocity);
	myStepper.setAcceleration(acceleration);
	myStepper.setSpeed(jogVelocity);
  //for endstop
  pinMode(endStopVcc, OUTPUT);
  pinMode(endStop, INPUT);
  digitalWrite(endStopVcc, HIGH);
  //for can bus
  CanBusMCP2515_asukiaaa::Settings settings(QUARTZ_FREQUENCY, BITRATE);
  Serial.begin(115200);
  Serial.println("settings:");
  Serial.println(settings.toString());
  //check can config
  while (true) {
    uint16_t errorCode = can.begin(settings);
    if (errorCode == 0) break;
    Serial.print("Configuration error: ");
    Serial.println(CanBusMCP2515_asukiaaa::Error::toString(errorCode));
    delay(1000);
  }
  Serial.print("CAN link successful!");
  //calibrated=1;
  //microCalib=1;
 // home = myStepper.currentPosition();
 calibrateRotor();
}


void homeRotor(){
  Serial.println("Homing..");
  myStepper.moveTo(home);
  while(myStepper.distanceToGo() == 0) {
    myStepper.moveTo(home);
    myStepper.run();
    delayMicroseconds(10);
  }
  return;
}

void sweepRotor(int direction=1, int sweepRange=50000) {
  //int i=10;
  endStopRead=digitalRead(endStop);
  while(endStopRead==0 && sweepRange>0){
    //i=10;
    myStepper.move(posPerRev * direction * gearRatio/360);
    myStepper.run();
    sweepRange-=1;
    delayMicroseconds(20);
    endStopRead=digitalRead(endStop);
    /*while (i){                                   //uncomment for debouncing endstop
      if (digitalRead(endStop)==0) {
        endStopRead=0;
      }
      i-=1;
      }*/
  }
  microCalib=endStopRead;
  return;
}

void calibrateRotor() {
  Serial.println ("\nCalibrating Rotor");
  while(digitalRead(endStop)==0){
    myStepper.move(posPerRev * 1 * gearRatio/360);
    myStepper.run();
    delayMicroseconds(10);
  }
  home = myStepper.currentPosition();
  Serial.print ("\nRotor Calibration Successful!\nHome found at ");
  Serial.println (home);
  calibrated=1;
  microCalib=1;
  return;
}


void microCalibrateRotor(){
  Serial.println("micro-calibrating at 0 degree..");
    Serial.println("forward sweeping..");
    sweepRotor(1,25000);
    if (!microCalib){
      Serial.println("centering");
      homeRotor();
      Serial.println("Reverse sweeping..");
      sweepRotor(-1,25000);
      
    }
    if (microCalib){
      Serial.println("micro-calibrated.");
      home = myStepper.currentPosition();
      Serial.print("New home at ");
      Serial.println(home);
      microCalib=1;
    }
    else {
      Serial.println("micro-calibration failed!");
      homeRotor();
      calibrateRotor();
    }
    return;
}


void loop() {
  digitalWrite(enPin, LOW);
  static unsigned long trySendAt = 0;
  static const unsigned long intervalMs = 1000UL;
  //if bus open
  if (can.available()) {
    CanBusData_asukiaaa::Frame frame;
    can.receive(&frame);
    angle = frame.data[5]+frame.data[4];
    steps = posPerRev * angle * gearRatio/360.0;
    steps = steps + home;

    //if master requested calibration or if rotor is uncalibrated. 
    //This halts every other process and enters calibration loop.
    if (frame.data[0]==1) {
      calibrateRotor();
    }
    //if already calibrated and master didn't request calibration
    //implement the angle read
    if (calibrated==1 && frame.data[0]==0) {
      Serial.print("\nSetting Angle to: ");
      Serial.println(angle);
      myStepper.moveTo(steps);
      angleFlag=1;
    }

    if(angle==0){microCalib=0;}
  }

  //micro calibrating 0
  if (microCalib==0 && myStepper.distanceToGo() == 0){
    microCalibrateRotor();
  }

  //report completed motion
  if (myStepper.distanceToGo() == 0 && angleFlag) 
    { 
      Serial.print("\nmoved to ");
      Serial.println(angle);
      angleFlag=0;
    }
	// Move the motor one step
	myStepper.run(); 
}

