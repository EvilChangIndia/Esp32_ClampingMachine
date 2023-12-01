// Define pin connections & motor's steps per revolution
const int dirPin = 26;
const int stepPin = 25;
const int enPin = 27;
const int stepsPerRevolution = 1600;

void setup()
{
	// Declare pins as Outputs
	pinMode(stepPin, OUTPUT);
	pinMode(dirPin, OUTPUT);
	pinMode(enPin, OUTPUT);
}
void loop()
{
  digitalWrite(enPin, LOW);
	// Set motor direction clockwise
	digitalWrite(dirPin, HIGH);

	// Spin motor slowly
	for(int x = 0; x < stepsPerRevolution; x++)
	{
		digitalWrite(stepPin, HIGH);
		delayMicroseconds(500);
		digitalWrite(stepPin, LOW);
		delayMicroseconds(500);
	}
	delay(1000); // Wait a second
	
	// Set motor direction counterclockwise
	digitalWrite(dirPin, LOW);

	// Spin motor quickly
	for(int x = 0; x < stepsPerRevolution; x++)
	{
		digitalWrite(stepPin, HIGH);
		delayMicroseconds(100);
		digitalWrite(stepPin, LOW);
		delayMicroseconds(100);
	}
	delay(1000); // Wait a second
}