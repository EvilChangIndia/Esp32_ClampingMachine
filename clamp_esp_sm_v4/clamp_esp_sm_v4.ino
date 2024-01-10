//machine states:-   100: FailSafe   0: OFF   1: ON   2: Unclamped    3: Clamped    4: Clamped    5: Update Angle   6:Stepper Run   
//frame send to master : {state, ack, status, 0, angle1, angle2, 0, 0}
//state: current state
//ack: 0:message received 1:not received
//status:   10:off successful, 11:on successful, 12: unclamp success, 13:calibration successful  14:clamp success 15:motion completed 0-9:curresponding errors. 110:failsafe entered
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
#define CAN_ID 2000
#endif

//for stepper
#include <AccelStepper.h>
#define motorInterfaceType 1
const int dirPin = 26;
const int stepPin = 25;
const int enPin = 27;
const int endStop = 32;
const int endStopVcc = 33;

//for clamp
const int clampPin = 4;
const int unclampPin = 0;


//some custom settings
const int posPerRev = 1600;          //for 1/8 micro stepping
const int gearRatio = 38;           //of the wormgear
const int maxVelocity = posPerRev*5;    //make it multiples of posPerRev
const int acceleration = maxVelocity/2;  //worked better this way. Will affect postioning accuracy
const int jogVelocity = 800;              //velocity at which myStepper.runSpeed() will move the rotor
const int sweepRange=10;
const int calibRevs = 2;
const int clampTime = 500; //time to complete clamping in milli-seconds
const int onTime = 1000; //startup time when turned on
const int homeAngle = 90;

//frame structure
//[stateID, free, free, free, angleA, angleB]
//required rotor angle = angleA + angleB
const int stateID = 0; 
const int angleAID = 4;
const int angleBID = 5;


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
int errorCode=0;

//Make instances for CAN bus & stepper
AccelStepper myStepper(motorInterfaceType, stepPin, dirPin);
CanBusMCP2515_asukiaaa::Driver can(PIN_CS, PIN_INT, PIN_RST);
CanBusMCP2515_asukiaaa::Settings settings(QUARTZ_FREQUENCY, BITRATE);
CanBusData_asukiaaa::Frame frame;

void setup() {
  //for stepper
  pinMode(enPin, OUTPUT);
  myStepper.setMaxSpeed(maxVelocity);
	myStepper.setAcceleration(acceleration);
	myStepper.setSpeed(jogVelocity);
  //for endstop
  pinMode(endStopVcc, OUTPUT);
  pinMode(endStop, INPUT);
  //clamp
  pinMode(clampPin, OUTPUT);
  pinMode(unclampPin, OUTPUT);
  //serial monitor settings
  Serial.begin(115200);
  Serial.println("settings:");
  Serial.println(settings.toString());
  //turn off all devices
  digitalWrite(enPin, HIGH);
  digitalWrite(endStopVcc, LOW);
  digitalWrite(unclampPin, HIGH); 
  digitalWrite(clampPin, HIGH); 
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
  home=0;
  angle=0;
  calibrated=1;
  microCalib=1;
  failSafeFlag=0;
  //Running the startup routine
  Serial.println("Running the startup routine..");
  startupRoutine();
}
//Function for unning the startup routine
void startupRoutine() {
  Serial.println("Device On..");
  digitalWrite(enPin, LOW);
  digitalWrite(endStopVcc, HIGH);
  Serial.println("Running initial calibration..");
  microCalibrateRotor();
  
}

//function for homing the rotor
void homeRotor()  {
  Serial.println("Homing..");
  setRotor(home);
  return;
}

//function for moving the rotor to given angle. 
//WARNING. This stops everything else from running
void setRotor(int a)  {
  Serial.print("Setting rotor to angle ");
  Serial.println(a);
  steps = (posPerRev * a * gearRatio/360.0);
  myStepper.moveTo(steps);
  myStepper.runToPosition();
  return;
}

//function to perform a complete calibration of the rotor
//this set's a new value to the home 
void calibrateRotor() 
{ 
  calibrated=0;
  Serial.println ("\nCalibrating Rotor");
  myStepper.move(posPerRev * calibRevs * gearRatio);
  int endStopRead = digitalRead(endStop);
  while(myStepper.distanceToGo() != 0)  {
    myStepper.run();
    delayMicroseconds(5);
    if (digitalRead(endStop)) {
      endStopRead = 1;
      home = myStepper.currentPosition()-100; //if home is found
      Serial.print ("\nHome found at : ");
      Serial.println (home);
      calibrated=1;
      myStepper.stop();
      myStepper.runToPosition();  //calls run() until motor comes to stop
      Serial.println ("\nReturning Home");
      myStepper.moveTo(home);
      myStepper.runToPosition();  //calls run() until motor reaches the target (home)
    }
  }
  if (calibrated)  {   //if home is found,
    Serial.println ("\nApplying changes..");
    home = posPerRev * homeAngle * gearRatio/360.0;
    myStepper.setCurrentPosition(home);
    Serial.println ("\nRotor Calibration Successful!");
    microCalib=1;
    canSend(2,13);
  }
  else  {
    state=-1;
    failSafeFlag=1;
    Serial.println ("Rotor Calibration Failed");
    canSend(2,3);
  }
  //send rotor back to angle before calibration
  setRotor(angle);
  return;
}

//function for sweeping rotor
//used by quick re-calibaration function
void sweepRotor(int direction=1, int sweep=20) 
{
  myStepper.move(posPerRev * direction * sweep * gearRatio/360);
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
  //homeRotor();
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
    myStepper.setCurrentPosition((posPerRev * homeAngle * gearRatio/360.0)+100);
    calibrated=1;
    canSend(2,13);
    //send rotor back to angle before calibration
    //setRotor(angle);
  }
  else {
    Serial.println("Rotor micro-calibration failed!\nTrying full calibration..");
    //homeRotor();
    calibrateRotor();
    return;
  }
  //send rotor back to angle before calibration
  setRotor(angle); //to cancel any residual movements
  return;
}

void failSafe() 
{
  Serial.println("\nFailsafe Mode activated");
  Serial.println("Disabling rotor");
  if (failSafeFlag==1)  Serial.println ("\nPlease ensure that the endstop is functional!");
  //if (failsafeFlag==2)
  digitalWrite(enPin, HIGH);
  digitalWrite(endStopVcc, LOW);
  digitalWrite(unclampPin, HIGH); 
  digitalWrite(clampPin, HIGH); 
  Serial.println("\nhelp meeeeee.... XP ");
  //while (true) ; //keep here
}

void clamp(bool engage)
{
  if (engage){
    Serial.println("Clamp is engaged..");
    digitalWrite(unclampPin, HIGH);  
    digitalWrite(clampPin, LOW);
    delay(1000);
    canSend(2,14);
  }
  else{
    Serial.println("Clamp is disengaged..");
    digitalWrite(clampPin, HIGH);  
    digitalWrite(unclampPin, LOW);
    delay(1000);
    canSend(2,12); //maybe needs while loop
  }

}
//function to receive message from the can bus and check it against the can id of the clamp (2000)
bool canReceive()
{
  if (can.available())
  {
    can.receive(&frame);
    if (frame.id==CAN_ID)
    {
      state = frame.data[stateID];
      angle = frame.data[angleAID]+frame.data[angleBID];
      canSend(1,1);
      return true;
      }
  }
  return false;
}

bool canSend(int i, int val)
{
  frame.id = CAN_ID;
  frame.ext = frame.id > 2048;
  frame.data[i]= val;
  while(!can.tryToSend(frame)){
    Serial.println("Sending again");
    Serial.println(val);
  }
  return 1;
  //return can.tryToSend(frame);
}



//THE MAIN LOOP
//myStepper.run() has to be called repeatedly in this loop for the library to work
//machine states:-   100: FailSafe   0: OFF   1: ON   2: Unclamped    3: Calibration    4: Clamped    5: Update Angle   6:Stepper Run   
//frame send to master : {state, ack, status, 0, angle1, angle2, 0, 0}
//state: current state
//ack: 0:message received 1:not received
//status:   10:off successful, 11:on successful, 12: unclamp success, 13:calibration successful  14:clamp success 15:motion completed 0-9:curresponding errors. 110:failsafe entered
void loop() 
{ 
  //Serial.println(canSend(1));
  switch(state) {
    case 100:  //Failsafe
      failSafe();
      canSend(2,110);
      while (!canReceive()) delay(50);//until there is a new message event
      break;

    case 0: //OFF state
      Serial.println("Device Off..");
      digitalWrite(enPin, HIGH);
      digitalWrite(endStopVcc, LOW);
      digitalWrite(unclampPin, HIGH); 
      digitalWrite(clampPin, HIGH); 
      canSend(2,10);
      while (!canReceive()) delay(50);//until there is a new message event
      break;

    case 1: //ON state
      Serial.println("Device On..");
      digitalWrite(enPin, LOW);
      digitalWrite(endStopVcc, HIGH);
      canSend(2,11);
      while (!canReceive()) delay(50);//until there is a new message event
      break;

    case 2: //Un-clamped state
      digitalWrite(enPin, LOW);
      digitalWrite(endStopVcc, HIGH);
      clamp(false);
      while (!canReceive()) delay(50);//until there is a new message event
      break;

    case 3: //Calibration State
      microCalibrateRotor();
      if (failSafeFlag)
      {
        state = -1;
        break;
      }
      while (!canReceive()) delay(50);//until there is a new message event
      break;

    case 4: //Clamped state
      digitalWrite(enPin, LOW);
      digitalWrite(endStopVcc, HIGH);
      clamp(true);
      while (!canReceive()) delay(50);//until there is a new message event
      break;

    case 5: //Update angle
      steps = (posPerRev * angle * gearRatio/360.0);
      myStepper.moveTo(steps);
      Serial.print("\nSetting target angle to : ");
      Serial.println(angle);
      state=6;

    case 6: //Stepper-rotation state
      int f=0;
      while (!canReceive()) {
        myStepper.run();
        if (myStepper.distanceToGo()==0 && f==0) {
          f=1;
          Serial.println("motion completed");
          bool i=canSend(2,15);
        }       
      }
      break;
    }
  //end of main loop
}