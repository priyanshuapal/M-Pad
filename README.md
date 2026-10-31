### M-Pad
A fully DIY, wirelessly connected physical StreamDeck and audio mixer. This project uses an Arduino Uno and an HC-05 Bluetooth module to communicate with a custom Python/CustomTkinter desktop application, providing zero-latency control over OBS Studio, VoiceMeeter Banana, Windows system audio, and keyboard macros.

## Features
* **25-Key Button Matrix:** Full 5x5 grid for executing macros, changing OBS scenes, or playing soundboard files.
* **4 Physical Sliders:** Analog volume control mapped to Windows apps or VoiceMeeter inputs/outputs (with built-in logarithmic audio tapering).
* **Wireless Bluetooth Connectivity:** Broadcasts serial data simultaneously over USB and Bluetooth (38400 baud) for a completely tether-free desk setup.
* **Hardware Profile Switching:** Physical toggle switch instantly swaps between layout profiles without touching the software.
* **Dedicated Z Button:** A standalone analog-read button for critical overrides or macros.
* **Auto-Reconnecting Python App:** A modern, dark-mode GUI that saves configurations to JSON and gracefully recovers from wireless dropouts.

## Hardware Requirements
* 1x Arduino Uno (or Nano)
* 26x Push Buttons (for the 5x5 matrix)
* 4x 10k Linear Potentiometers (Sliders)
* 1x SPDT Toggle Switch (for Profile Switching)
* 1x HC-05 or HC-06 Bluetooth Module (flashed to 38400 baud)
* 10kΩ Pull-down resistors (as needed for analog buttons)

## Wiring & Pinout (Uno V1)

| Component | Arduino Pin | Notes |
| :--- | :--- | :--- |
| **Matrix Rows** | `D2, D3, D4, D5, D6` | 5x5 Keypad.h Matrix |
| **Matrix Cols** | `D7, D8, D9, D10, D11`| 5x5 Keypad.h Matrix |
| **HC-05 RX** | `D12` | Connected via SoftwareSerial |
| **HC-05 TX** | `D13` | Connected via SoftwareSerial |
| **Sliders 1-4** | `A0, A2, A3, A4` | Analog Volume Control |
| **Z Button** | `A1` | Reads via analog threshold (`< 950`) |
| **Profile Switch**| `A5` | Internal pull-up, toggles High/Low |

## Software Installation

### 1. Arduino Setup
1. Open the `.ino` sketch in the Arduino IDE.
2. Install the `Keypad` and `SoftwareSerial` libraries via the Library Manager.
3. Flash the code to your Arduino Uno.

### 2. Python App Setup
This application requires Python 3.8+. To install the required dependencies, run:

```bash
pip install customtkinter pyserial pyautogui obsws_python pygame pycaw voicemeeterlib
