/*
  Blink without Delay

  Turns on and off a light emitting diode (LED) connected to a digital pin,
  without using the delay() function. This means that other code can run at the
  same time without being interrupted by the LED code.

  The circuit:
  - Use the onboard LED.
  - Note: Most Arduinos have an on-board LED you can control. On the UNO, MEGA
    and ZERO it is attached to digital pin 13, on MKR1000 on pin 6. LED_BUILTIN
    is set to the correct LED pin independent of which board is used.
    If you want to know what pin the on-board LED is connected to on your
    Arduino model, check the Technical Specs of your board at:
    https://www.arduino.cc/en/Main/Products

  created 2005
  by David A. Mellis
  modified 8 Feb 2010
  by Paul Stoffregen
  modified 11 Nov 2013
  by Scott Fitzgerald
  modified 9 Jan 2017
  by Arturo Guadalupi

  This example code is in the public domain.

  https://www.arduino.cc/en/Tutorial/BuiltInExamples/BlinkWithoutDelay
*/

// constants won't change. Used here to set a pin number:
const int valve1 =4;  // the number of the LED pin
const int valve2 =0;
// Variables will change:
int on = LOW;  // ledState used to set the LED
int off = HIGH;
// Generally, you should use "unsigned long" for variables that hold time
// The value will quickly become too large for an int to store
unsigned long previousMillis = 0;  // will store last time LED was updated

// constants won't change:
const long interval = 1000;  // interval at which to blink (milliseconds)

void setup() {
  // set the digital pin as output:
  pinMode(valve1, OUTPUT);
  pinMode(valve2, OUTPUT);
  digitalWrite( valve1, off);
  digitalWrite( valve2, off);
  Serial.begin(115200);
}

void loop() {
  digitalWrite( valve2, HIGH);
  digitalWrite( valve1, LOW);
  Serial.println(on,off);
  delay(3000);
  digitalWrite( valve1, HIGH);
  digitalWrite( valve2, LOW);
  Serial.println(off,on);
  delay(3000);
}
