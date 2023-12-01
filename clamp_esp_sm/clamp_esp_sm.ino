
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

//for stepper
#include <AccelStepper.h>
#define motorInterfaceType 1
const int dirPin = 26;
const int stepPin = 25;
const int enPin = 27;
const int endStop = 33;
const int endStopVcc = 32;

//some custom settings
const int posPerRev = 1600;          //for 1/8 micro stepping
const int gearRatio = 38;           //of the wormgear
const int maxVelocity = posPerRev*10;    //make it multiples of posPerRev
const int acceleration = maxVelocity/2;  //worked better this way. Will affect postioning accuracy
const int jogVelocity = 800;              //velocity at which myStepper.runSpeed() will move the rotor
const int sweepRange=10;
const int calibRevs = 2;
const int clampTime = 3000; //time to complete clamping in milli-seconds
const int onTime = 1000; //startup time when turned on
const int stateID=0;


//some global variables
int steps=0;
int revolutions = 1;
int home=0;
int angle=0;
int inMotion=0;
int calibrated=1;
int microCalib=1;
int failSafeFlag = 0;  //use this to ID different types of errors
int state=0;

//Make instances for CAN bus & stepper
AccelStepper myStepper(motorInterfaceType, stepPin, dirPin);
CanBusMCP2515_asukiaaa::Driver can(PIN_CS, PIN_INT, PIN_RST);
CanBusMCP2515_asukiaaa::Settings settings(QUARTZ_FREQUENCY, BITRATE);

void setup() {
  //for stepper
  pinMode(enPin, OUTPUT);
  myStepper.setMaxSpeed(maxVelocity);
	myStepper.setAcceleration(acceleration);
	myStepper.setSpeed(jogVelocity);
  //for endstop
  pinMode(endStopVcc, OUTPUT);
  pinMode(endStop, INPUT);
  //serial monitor settings
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
  Serial.println("CAN link successful!");
  //CanBusData_asukiaaa::Frame frame;
  //initialise variables
  steps=0;
  home=0;
  inMotion=0;
  //initialise state variables
  state=0;
  angle=0;
  calibrated=1;
  microCalib=1;
  failSafeFlag=0;

}

//some functions

//function for homing the rotor
void homeRotor()  {
  Serial.println("Homing..");
  myStepper.moveTo(home);
  while(myStepper.distanceToGo() != 0)  {
    myStepper.run();
    delayMicroseconds(10);
  }
  return;
}

//function for moving the rotor to given angle. 
//WARNING. This stops everything else from running
void setRotor(int a)  {
  Serial.print("\nMoving to angle : ");
  Serial.println(a);
  myStepper.moveTo(a);
  while(myStepper.distanceToGo() != 0)  {
    myStepper.run();
    delayMicroseconds(10);
  }
  return;
}

//function to perform a complete calibration of the rotor
//this set's a new value to the home 
void calibrateRotor() 
{
  Serial.println ("\nCalibrating Rotor");
  myStepper.move(posPerRev * calibRevs * gearRatio);
  int endStopRead = digitalRead(endStop);
  while(endStopRead==0 && myStepper.distanceToGo() != 0)  {
    myStepper.run();
    delayMicroseconds(10);
    endStopRead = digitalRead(endStop);
  }
  if (endStopRead==1)  {   //if home is found,
    home = myStepper.currentPosition(); //update new home position       
    Serial.print ("\nRotor Calibration Successful!\nHome found at ");
    Serial.println (home);
    calibrated=1;
    microCalib=1;
  }
  else  {
    failSafeFlag=1;  
    Serial.println ("Rotor Calibration Failed");
  }
  //send rotor back to angle before calibration

  //setRotor(angle);

  myStepper.moveTo(home); //to cancel any residual movements
  return;
}

//function for sweeping rotor
//used by quick re-calibaration function
void sweepRotor(int direction=1, int sweep=20) 
{
  myStepper.move(posPerRev * direction*sweep* gearRatio/360);
  int endStopRead = digitalRead(endStop);
  while(endStopRead==0 && myStepper.distanceToGo() != 0)  {
    myStepper.run();
    delayMicroseconds(10);
    endStopRead = digitalRead(endStop);
  }  
  microCalib = endStopRead;
  return;
}

//function for a quick re-calibaration through small sweeps
void microCalibrateRotor()
{
  int centre = myStepper.currentPosition();
  Serial.println("micro-calibrating ..");
  Serial.println("forward sweeping..");
  sweepRotor(1,sweepRange); //this sets microCalib to 1 if home is found
  if (!microCalib){
    Serial.println("centering");
    setRotor(centre);
    Serial.println("Reverse sweeping..");
    sweepRotor(-1,sweepRange);  
  }
  if (microCalib){
    Serial.println("micro-calibrated.");
    home = myStepper.currentPosition();
    Serial.print("New home at ");
    Serial.println(home);
    calibrated=1;
    //send rotor back to angle before calibration
    //setRotor(angle);
  }
  else {
    Serial.println("Rotor micro-calibration failed!\nTrying full calibration..");
    //homeRotor();
    calibrateRotor();
  }
  myStepper.moveTo(home); //to cancel any residual movements
  return;
}

void failSafe() 
{
  Serial.println("\nFailsafe Mode activated");
  Serial.println("Disabling rotor");
  if (failSafeFlag==1)  Serial.println ("\nPlease ensure that the endstop is functional!");
  //if (failsafeFlag==2)
  digitalWrite(enPin, HIGH);
  Serial.println("\nhelp meeeeee.... XP ");
  while (true) ; //keep here
}

//THE MAIN LOOP
//myStepper.run() has to be called repeatedly in this loop for the library to work
/*
void loop() 
{
  if (failSafeFlag) failSafe();
  digitalWrite(enPin, LOW);
  //INPUT EVENT
  if (can.available()) {            //if there is a new message event
    CanBusData_asukiaaa::Frame frame;
    can.receive(&frame);
    angle = frame.data[5]+frame.data[4];
    steps = posPerRev * angle * gearRatio/360.0;
    steps = steps + home;

    //CALIBRATION STATE
    if (frame.data[0]==1) microCalibrateRotor(); //if master requested calibration 

    //UPDATE ROTOR ANGLE STATE
    else if (calibrated==1) {       //if already calibrated and it's not a calibration request,
      Serial.print("\nSetting Angle to: ");
      Serial.println(angle);
      myStepper.moveTo(steps);      //updates the target rotor position for run() command
      inMotion=1;
      //microcalibrate everytime we are at 0 degree,
      //if it was not a calibration request
      if(angle==0)  microCalib=0;
    }
  }

  //report completed motion
  if (myStepper.distanceToGo() == 0 && inMotion) 
    { 
      Serial.print("\nmoved to ");
      Serial.println(angle);
      inMotion=0;
    }

  //microcalibrate everytime we are at 0 degree,
  if (myStepper.currentPosition() == home && microCalib == 0) 
    {
      Serial.println("At zero.\nInterrupting for micro calibration..");
      microCalibrateRotor();
      //making sure that we don't miss the command received right after 0
      if (angle) myStepper.moveTo(angle);
    }
	// Move the motor one step. This needs to be called repeatedly, in main loop, for continuous stepper motion.
	myStepper.run(); 
}*/
////////

///////

void loop() 
{ 
  CanBusData_asukiaaa::Frame frame;
  //machine states:-   0: OFF   1: ON   2: Unclamped    3: Clamped    4: Clamped    5: Update Angle   6:Stepper Run  
  //INPUT EVENT
  if (can.available()) {            //if there is a new message event    
    can.receive(&frame);
    state = frame.data[stateID];
    }
  switch(state) {
      case 0:
      Serial.println("Device Off..");
      digitalWrite(enPin, HIGH);
      while (!can.available());//until there is a new message event
      break;

      case 1:
      Serial.println("Device On..");
      digitalWrite(enPin, LOW);
      digitalWrite(endStopVcc, HIGH);
      delay(onTime); //let it fall through to unclamped state
      state = 2;

      case 2:
      Serial.println("Clamp is disengaged..");
      while (!can.available());//until there is a new message event
      break;

      case 3:
      microCalibrateRotor();
      while (!can.available());//until there is a new message event
      break;

      case 4:
      Serial.println("Clamp is engaged..");
      delay(clampTime);
      while (!can.available());//until there is a new message event
      break;

      case 5:
      angle = frame.data[5]+frame.data[4];
      steps = posPerRev * angle * gearRatio/360.0;
      steps = steps + home;
      myStepper.moveTo(steps);
      Serial.print("\nSetting target angle to : ");
      Serial.println(angle);
      state=6;

      case 6:
      myStepper.run();

    }
}
  
/*
    angle = frame.data[5]+frame.data[4];
    steps = posPerRev * angle * gearRatio/360.0;
    steps = steps + home;

    //CALIBRATION STATE
    if (frame.data[0]==1) microCalibrateRotor(); //if master requested calibration 

    //UPDATE ROTOR ANGLE STATE
    else if (calibrated==1) {       //if already calibrated and it's not a calibration request,
      Serial.print("\nSetting Angle to: ");
      Serial.println(angle);
      myStepper.moveTo(steps);      //updates the target rotor position for run() command
      inMotion=1;
      //microcalibrate everytime we are at 0 degree,
      //if it was not a calibration request
      if(angle==0)  microCalib=0;
    }
  }

  //report completed motion
  if (myStepper.distanceToGo() == 0 && inMotion) 
    { 
      Serial.print("\nmoved to ");
      Serial.println(angle);
      inMotion=0;
    }

  //microcalibrate everytime we are at 0 degree,
  if (myStepper.currentPosition() == home && microCalib == 0) 
    {
      Serial.println("At zero.\nInterrupting for micro calibration..");
      microCalibrateRotor();
      //making sure that we don't miss the command received right after 0
      if (angle) myStepper.moveTo(angle);
    }
	// Move the motor one step. This needs to be called repeatedly, in main loop, for continuous stepper motion.
	myStepper.run(); 
}*/