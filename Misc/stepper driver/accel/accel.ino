// Include the AccelStepper Library
#include <AccelStepper.h>
// Define motor interface type
#define motorInterfaceType 1
// Define pin connections
const int dirPin = 26;
const int stepPin = 25;
const int enPin = 27;

//some custom settings
const int posPerRev = 800;          //for 1/8 micro stepping
//experiment for other steps
const int gearRatio = 38;           //of the wormgear
int maxVelocity = posPerRev*20;    //make it multiples of posPerRev
int acceleration = max_velocity/2;  //worked better this way. Will affect postioning accuracy
int jogVelocity = 500;
int revolutions = 1;



// Creates an instance
AccelStepper myStepper(motorInterfaceType, stepPin, dirPin);

void setup() {
  pinMode(enPin, OUTPUT);
	// set the maximum speed, acceleration factor,
	// initial speed and the target position
	myStepper.setMaxSpeed(maxVelocity);
	myStepper.setAcceleration(acceleration);
	myStepper.setSpeed(jogVelocity);
	myStepper.moveTo(posPerRev * revolutions * gearRatio);
}

void loop() {
  digitalWrite(enPin, LOW);
	// Change direction once the motor reaches target position
	if (myStepper.distanceToGo() == 0) 
    {
      delay(2000);
      myStepper.moveTo(-myStepper.currentPosition());
    }
	// Move the motor one step
	myStepper.run(); 
  
}