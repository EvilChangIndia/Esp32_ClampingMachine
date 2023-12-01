
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
  home=0;
  calibrated=1;
  microCalib=1;
  failSafeFlag=0;

}

//function for homing the rotor
void homeRotor()  {
  Serial.println("Homing..");
  setRotor(0);
  return;
}

//function for moving the rotor to given angle. 
//WARNING. This stops everything else from running
void setRotor(int a)  {
  steps = posPerRev * a * gearRatio/360.0;
  steps = steps + home;
  myStepper.moveTo(steps);
  while(myStepper.distanceToGo() != 0)  myStepper.run();
  return;
}

//function to perform a complete calibration of the rotor
//this set's a new value to the home 
void calibrateRotor() 
{ 
  calibrated=0;
  homeRotor();
  Serial.println ("\nCalibrating Rotor");
  myStepper.move(posPerRev * calibRevs * gearRatio);
  int endStopRead = digitalRead(endStop);
  while(myStepper.distanceToGo() != 0)  {
    myStepper.run();
    delayMicroseconds(5);
    if (digitalRead(endStop)) {
      endStopRead = 1;
      home = myStepper.currentPosition()-100; //if home is found
      calibrated=1;
      myStepper.stop();
    }
  }
  if (calibrated)  {   //if home is found,
    Serial.print ("\nRotor Calibration Successful!\nHome found at ");
    Serial.println (home);
    microCalib=1;
  }
  else  {
    state=-1;
    failSafeFlag=1;
    Serial.println ("Rotor Calibration Failed");
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
  homeRotor();
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
void loop() 
{ 
  CanBusData_asukiaaa::Frame frame;
  //machine states:-   -2: MasterSynch    -1: FailSafe   0: OFF   1: ON   2: Unclamped    3: Clamped    4: Clamped    5: Update Angle   6:Stepper Run   
  switch(state) {
    case -2:         //if there is a new message event
      can.receive(&frame);
      state = frame.data[stateID];
      //Serial.print("\nnew state is ");
      //Serial.println(state);
      angle = frame.data[angleAID]+frame.data[angleBID];
      steps = posPerRev * angle * gearRatio/360.0;
      steps = steps + home;
      break;
    
    case -1:
      failSafe();
      while (!can.available());//until there is a new message event
      state = -2;
      break;

    case 0:
      Serial.println("Device Off..");
      digitalWrite(enPin, HIGH);
      digitalWrite(endStopVcc, LOW);
      while (!can.available());//until there is a new message event
      state = -2;
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
      state = -2;
      break;

    case 3:
      microCalibrateRotor();
      while (!can.available());//until there is a new message event
      state = -2;
      break;

    case 4:
      Serial.println("Clamp is engaged..");
      delay(clampTime);
      while (!can.available());//until there is a new message event
      state = -2;
      break;

    case 5:
      myStepper.moveTo(steps);
      Serial.print("\nSetting target angle to : ");
      Serial.println(angle);
      state=6;

    case 6:
      while (!can.available()) myStepper.run();
      state = -2;
      break;

    }
}