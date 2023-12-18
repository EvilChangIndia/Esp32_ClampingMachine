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

CanBusMCP2515_asukiaaa::Driver can(PIN_CS, PIN_INT, PIN_RST);

void setup() {
  CanBusMCP2515_asukiaaa::Settings settings(QUARTZ_FREQUENCY, BITRATE);
  Serial.begin(9600);
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
  Serial.print("Succeeced in beginning");
}

void loop() {
  static unsigned long trySendAt = 0;
  static const unsigned long intervalMs = 1000UL;
  if (trySendAt == 0 || millis() - trySendAt > intervalMs) {
    trySendAt = millis();
    CanBusData_asukiaaa::Frame frame;
    frame.id = CAN_ID;
    frame.ext = frame.id > 2048;
    frame.data64 = 12;
    // frame.idx = frame.data64 % 3;
    const bool ok = can.tryToSend(frame);
    Serial.println("Sent");
    Serial.println(frame.toString());
    Serial.print(ok ? "Succeeded" : "Failed");
    Serial.print(" at ");
    Serial.println(trySendAt);
  }
  if (can.available()) {
    CanBusData_asukiaaa::Frame frame;
    can.receive(&frame);
    Serial.println("Received");
    /*Serial.println(frame.toString());
    Serial.print("at ");
    Serial.println(millis());*/
    int a = frame.id;
    Serial.println(a);
  }
  delay(10);
}
