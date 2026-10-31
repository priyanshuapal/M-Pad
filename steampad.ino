#include <Keypad.h>
#include <SoftwareSerial.h>

// --- BLUETOOTH SETUP ---
// RX pin is 12, TX pin is 13
SoftwareSerial btSerial(12, 13); 

// --- MATRIX SETUP ---
const byte ROWS = 5; 
const byte COLS = 5; 
char keys[ROWS][COLS] = {
  {'A','B','C','D','E'},
  {'F','G','H','I','J'},
  {'K','L','M','N','O'},
  {'P','Q','R','S','T'},
  {'U','V','W','X','Y'}
};

byte rowPins[ROWS] = {2, 3, 4, 5, 6}; 
byte colPins[COLS] = {7, 8, 9, 10, 11}; 

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// --- SLIDER SETUP ---
const int NUM_SLIDERS = 6;
// Added A0 to the sliders, skipping A1 for the button
int sliderPins[NUM_SLIDERS] = {A0, A2, A3, A4, A5, A6}; 
int lastSliderVals[NUM_SLIDERS] = {0};
const int SLIDER_TOLERANCE = 2; 

// --- SPECIAL ANALOG BUTTONS ---
const int BTN_Z_PIN = A1; // Changed from A0 to A1
const int THRESHOLD = 950; 

bool last_z_state = false;
unsigned long last_z_debounce = 0;

void setup() {
  Serial.begin(9600);   // USB Serial
  btSerial.begin(9600); // Bluetooth Serial
}

// Helper function to send commands to both USB and Bluetooth instantly
void sendCommand(String prefix, String value) {
  String fullCommand = prefix + value;
  Serial.println(fullCommand);
  btSerial.println(fullCommand);
}

void loop() {
  // 1. Matrix Buttons
  char key = keypad.getKey();
  if (key) {
    sendCommand("BTN:", String(key));
  }

  // 2. Analog Sliders
  for (int i = 0; i < NUM_SLIDERS; i++) {
    int raw_val = analogRead(sliderPins[i]);
    int mapped_val = map(raw_val, 0, 1023, 0, 100);
    
    if (abs(mapped_val - lastSliderVals[i]) > SLIDER_TOLERANCE) {
      lastSliderVals[i] = mapped_val;
      sendCommand("SLIDER_" + String(i + 1) + ":", String(mapped_val));
    }
  }

  // 3. Special Button Z (A1)
  int raw_z = analogRead(BTN_Z_PIN);
  bool current_z_state = (raw_z < THRESHOLD);
  
  if (current_z_state != last_z_state) {
    if (millis() - last_z_debounce > 50) {
      if (current_z_state == true) {
        sendCommand("BTN:", "Z");
      }
      last_z_state = current_z_state;
      last_z_debounce = millis();
    }
  }
  
  delay(10); 
}