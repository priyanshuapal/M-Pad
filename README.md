# M-Pad
A fully DIY, wirelessly connected physical StreamDeck and audio mixer. This project uses an Arduino Uno and an HC-05 Bluetooth module to communicate with a custom Python/CustomTkinter desktop application, providing zero-latency control over OBS Studio, VoiceMeeter Banana, Windows system audio, and keyboard macros.

### Hardware v1.1 of device 

<img width="2548" height="2548" alt="IMG_20261031_195119" src="https://github.com/user-attachments/assets/2464dcd2-82bc-47dd-89e6-d75a3561310b" />



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

<img width="928" height="939" alt="Screenshot (98)" src="https://github.com/user-attachments/assets/1eea63c8-48e6-4c74-8285-d6a5b587dbba" />



## Software Installation

### 1. Arduino Setup
1. Open the `.ino` sketch in the Arduino IDE.
2. Install the `Keypad` and `SoftwareSerial` libraries via the Library Manager.
3. Flash the code to your Arduino Uno.

### 2. Python App Setup
This application requires Python 3.8+. To install the required dependencies, run:

```bash
pip install customtkinter pyserial pyautogui obsws_python pygame pycaw voicemeeterlib
```

## Useage Instructions
### 1. Connect the Hardware
Open the app and select your Arduino's USB or Bluetooth COM port from the dropdown. Toggle "Auto-Connect on Startup" to automate this process on future launches.

### 2. Link OBS Studio (Optional)
Enable the WebSocket server in OBS (Tools > WebSocket Server Settings). Enter your port (default 4455) and password into the app, then toggle "Enable OBS Connection".

### 3. Map Grid Buttons
    Navigate to the "Button Matrix" tab. Select an action type from the dropdown for any letter (A-Y, plus Z).

    Keyboard & Media Macros: Select "Keyboard Shortcut", click the gear icon, and press your desired key combination. This natively supports Windows media keys (Play/Pause [playpause], Next Track [nexttrack], Previous Track [prevtrack], Mute).

    OBS Actions: Select a scene/transition action and enter the exact Scene Name or Index number in the target box.

    Soundboard: Select "Soundboard (Audio File)" and click the gear icon to browse for an .mp3 or .wav file.

### 4. Map Analog Sliders
Navigate to the "Slider Matrix" tab. Type your desired audio target into the text box:

    Type system for master Windows volume.

    Type an app name like spotify, chrome, or discord for specific application volumes.

    Type strip 0 or bus 1 for direct VoiceMeeter decibel control.

### 5. Manage Hardware Profiles
Flip the physical toggle switch (pin A5) on your hardware. The UI will instantly detect the hardware state and switch between Profile 1 and Profile 2, providing a completely blank canvas for new mappings. Click "Save to Profile" to write your configurations to the local deck_config.json file.
