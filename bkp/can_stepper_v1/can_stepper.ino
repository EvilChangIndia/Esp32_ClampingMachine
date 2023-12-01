
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
const int endStopVcc = 34;



//for stepper
#include <AccelStepper.h>
#define motorInterfaceType 1
//some custom settings
const int posPerRev = 1600;          //for 1/8 micro stepping
//experiment for other steps
const int gearRatio = 38;           //of the wormgear
int maxVelocity = posPerRev*14;    //make it multiples of posPerRev
int acceleration = maxVelocity/2;  //worked better this way. Will affect postioning accuracy
int jogVelocity = 500;
int revolutions = 1;
int angle1=0;
int flag=0;
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
  pinMode(endStop, OUTPUT);

  digitalWrite(endStopVcc, HIGH);
  
  //for can bus
  CanBusMCP2515_asukiaaa::Settings settings(QUARTZ_FREQUENCY, BITRATE);
  Serial.begin(115200);
  Serial.println("settings:");
  Serial.println(settings.toString());
  // while(!Serial) { delay(10); }
  while (true) {
    uint16_t errorCode = can.begin(settings);
    // uint16_t errorCode = can.begin(settings, [] { can.isr(); }); // attachInterrupt to INT pin
    if (errorCode == 0) break;
    Serial.print("Configuration error: ");
    Serial.println(CanBusMCP2515_asukiaaa::Error::toString(errorCode));
    delay(1000);
  }
  Serial.print("CAN link successful!");
}

void loop() {
  digitalWrite(enPin, LOW);
  static unsigned long trySendAt = 0;
  static const unsigned long intervalMs = 1000UL;

  if (can.available()) {
    CanBusData_asukiaaa::Frame frame;
    can.receive(&frame);
    angle1= frame.data[5]+frame.data[4];
    Serial.print("\nSetting Angle to: ");
    Serial.println(angle1);
    myStepper.moveTo(posPerRev * angle1 * gearRatio/360);
    //myStepper.moveTo(posPerRev * angle1/360);
    //myStepper.moveTo(posPerRev );
    flag=1;
  }
  if (myStepper.distanceToGo() == 0 && flag) 
    {
      Serial.print("\nmoved to ");
      Serial.println(angle1);
      flag=0;
    }
	// Move the motor one step
	myStepper.run(); 
}
