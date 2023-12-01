#include <math.h>
int fsrPin = 36;     // the FSR and 10K pulldown are connected to a0
int fsrReading;     // the analog reading from the FSR resistor divider
int fsrVoltage;     // the analog reading converted to voltage
unsigned long fsrGrams;
unsigned long fsrResistance;  // The voltage converted to resistance
unsigned long fsrConductance; 
long fsrForce;       // Finally, the resistance converted to force
 
void setup(void) {
  Serial.begin(9600);   // We'll send debugging information via the Serial monitor
}
 
void loop(void) {
  fsrReading = analogRead(fsrPin);  
  Serial.print("Analog reading = ");
  Serial.println(fsrReading);
  //Serial.println(fsrReading);
 
  // analog voltage reading ranges from about 0 to 1023 which maps to 0V to 5V (= 5000mV)
  fsrVoltage = map(fsrReading, 0, 4095, 0, 3300);
  Serial.print("Voltage reading in mV = ");
  Serial.println(fsrVoltage);  
 
  if (fsrVoltage == 0) {
    Serial.println("No pressure");  
  } else{
    // The voltage = Vcc * R / (R + FSR) where R = 10K and Vcc = 5V
    // so FSR = ((Vcc - V) * R) / V        yay math!
    fsrResistance = 3300 - fsrVoltage;     // fsrVoltage is in millivolts so 5V = 5000mV
    fsrResistance *= 10000;                // 10K resistor
    fsrResistance /= fsrVoltage;
    Serial.print("FSR resistance in ohms = ");
    Serial.println(fsrResistance);
    if (fsrResistance>25000){
      Serial.println("below range");
    }
    else if(fsrResistance<7000){
      Serial.println("above range");
    }
    else{
    fsrGrams = - 0.0000000011* pow(fsrResistance,3) + 0.0000626641*pow(fsrResistance,2) - 1.2590600846*fsrResistance +9458.414;
    Serial.print("Kgf: ");
    Serial.println(fsrGrams/1000.0);  }
   // Serial.println(pow(3,2));   
    
  }
  Serial.println("--------------------");
  delay(1000);
}