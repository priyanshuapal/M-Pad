import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
import json
import os
import sys
import pyautogui
import obsws_python as obs
import pygame
import pygame._sdl2.audio as sdl2_audio
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioEndpointVolume
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL, CoInitialize
import voicemeeterlib
import math
import customtkinter as ctk

# --- Path Setup for Persistent Config ---
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
    
CONFIG_FILE = os.path.join(base_path, "deck_config.json")

# Initialize Pygame core so we can probe audio devices
pygame.init()

class ModernStreamDeck(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Custom StreamDeck & Mixer")
        self.geometry("700x750")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.arduino = None
        self.obs_client = None
        self.is_running = False
        
        self.grid_buttons = {}
        self.slider_bars = {}
        self.bulk_btn_widgets = {}
        self.bulk_slider_widgets = {}
        self.active_record_var = None
        
        # --- Fetch available audio devices for Soundboard ---
        try:
            self.audio_devices = ["System Default"] + [sdl2_audio.get_audio_device_name(i, 0) for i in range(sdl2_audio.get_num_audio_devices(0))]
        except Exception:
            self.audio_devices = ["System Default"]
            
        # --- VoiceMeeter Connection ---
        try:
            # Change this to 'potato' or 'basic' if you aren't using Banana
            self.vm = voicemeeterlib.api('banana') 
            self.vm.login()
            print("Connected to VoiceMeeter Banana!")
        except Exception as e:
            print(f"VoiceMeeter connection failed: {e}")
            self.vm = None
        
        # --- GENERATE CUSTOM DEFAULTS ---
        default_buttons = {}
        
        # A-J: OBS Smart Scene (1-10)
        for i in range(10):
            default_buttons[chr(65 + i)] = {"type": "OBS Smart Scene (Index)", "target": str(i + 1)}
            
        # P-T: D-Pad and OK
        dpad_keys = ["up", "down", "left", "right", "enter"]
        for i, letter in enumerate(['P', 'Q', 'R', 'S', 'T']):
            default_buttons[letter] = {"type": "Keyboard Shortcut", "target": dpad_keys[i]}
            
        # Z: A0 Hardware Transition Button
        default_buttons['Z'] = {"type": "OBS Transition", "target": ""}
        
        self.config = {
            "serial_port": "",
            "use_obs": True,
            "obs_host": "localhost",
            "obs_port": "4455",
            "obs_password": "",
            "autoconnect": False,
            "audio_device": "System Default",
            "buttons": default_buttons,
            "sliders": {"1": "strip 3"} # Example default to VoiceMeeter VAIO for Banana
        }
        
        self.load_config()
        self.init_audio_mixer()
        self.build_ui()
        
        if self.config["autoconnect"]:
            self.toggle_connection()
            
    def init_audio_mixer(self):
        pygame.mixer.quit()
        device = self.config.get("audio_device", "System Default")
        try:
            if device == "System Default" or device not in self.audio_devices:
                pygame.mixer.init()
            else:
                pygame.mixer.init(devicename=device)
        except Exception as e:
            print(f"Audio init failed for {device}: {e}")
            pygame.mixer.init()
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
                for k in self.config:
                    if k in saved:
                        if isinstance(self.config[k], dict):
                            self.config[k].update(saved[k])
                        else:
                            self.config[k] = saved[k]
                
    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
            
    def get_com_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports] if ports else ["No Ports Found"]
            
    def build_ui(self):
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(expand=True, fill="both", padx=20, pady=20)
        
        tab_conn = self.tabs.add("Connection")
        tab_map = self.tabs.add("Button Matrix")
        tab_sliders = self.tabs.add("Slider Matrix")
        tab_test_btns = self.tabs.add("Test Buttons")
        tab_test_sliders = self.tabs.add("Test Sliders")
        
        # --- TAB 1: CONNECTION ---
        ctk.CTkLabel(tab_conn, text="Arduino COM Port:").pack(pady=(10, 5))
        
        port_frame = ctk.CTkFrame(tab_conn, fg_color="transparent")
        port_frame.pack(pady=5)
        self.port_var = ctk.StringVar(value=self.config["serial_port"])
        self.port_dropdown = ctk.CTkComboBox(port_frame, variable=self.port_var, values=self.get_com_ports())
        self.port_dropdown.pack(side="left", padx=5)
        ctk.CTkButton(port_frame, text="↻", width=30, command=lambda: self.port_dropdown.configure(values=self.get_com_ports())).pack(side="left")
        
        self.use_obs_var = ctk.BooleanVar(value=self.config["use_obs"])
        ctk.CTkSwitch(tab_conn, text="Enable OBS Connection", variable=self.use_obs_var).pack(pady=10)
        
        ctk.CTkLabel(tab_conn, text="OBS Password:").pack(pady=5)
        self.obs_pass_var = ctk.StringVar(value=self.config["obs_password"])
        ctk.CTkEntry(tab_conn, textvariable=self.obs_pass_var, show="*").pack(pady=5)
        
        ctk.CTkLabel(tab_conn, text="Soundboard Output Device:").pack(pady=(15, 5))
        self.audio_dev_var = ctk.StringVar(value=self.config["audio_device"])
        self.audio_dropdown = ctk.CTkComboBox(tab_conn, variable=self.audio_dev_var, values=self.audio_devices, width=300, command=self.change_audio_device)
        self.audio_dropdown.pack(pady=5)
        
        self.autoconnect_var = ctk.BooleanVar(value=self.config["autoconnect"])
        ctk.CTkSwitch(tab_conn, text="Auto-Connect on Startup", variable=self.autoconnect_var, command=self.save_connection_settings).pack(pady=15)
        
        self.connect_btn = ctk.CTkButton(tab_conn, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(pady=10)
        
        self.status_lbl = ctk.CTkLabel(tab_conn, text="Status: Disconnected", text_color="red")
        self.status_lbl.pack()

        # --- TAB 2: BUTTON MATRIX ---
        btn_scroll = ctk.CTkScrollableFrame(tab_map)
        btn_scroll.pack(fill="both", expand=True, pady=10)
        
        action_options = [
            "OBS Smart Scene (Index)",
            "OBS Scene (Live/Name)", 
            "OBS Preview (Name)", 
            "OBS Transition",
            "Keyboard Shortcut",
            "Soundboard (Audio File)",
            "Stop Soundboard"
        ]

        letters = [chr(65 + i) for i in range(25)] + ['Z']
        
        for letter in letters:
            row_frame = ctk.CTkFrame(btn_scroll, fg_color="transparent")
            row_frame.pack(fill="x", pady=4)
            
            lbl_text = f"Button {letter}" if letter != 'Z' else "A0 Button (Z)"
            ctk.CTkLabel(row_frame, text=lbl_text, width=80, anchor="w").pack(side="left", padx=5)
            
            saved_type = self.config["buttons"].get(letter, {}).get("type", "Keyboard Shortcut")
            saved_target = self.config["buttons"].get(letter, {}).get("target", "")
            
            type_var = ctk.StringVar(value=saved_type)
            type_cb = ctk.CTkComboBox(row_frame, variable=type_var, values=action_options, width=175)
            type_cb.pack(side="left", padx=5)
            
            target_var = ctk.StringVar(value=saved_target)
            target_entry = ctk.CTkEntry(row_frame, textvariable=target_var, width=180)
            target_entry.pack(side="left", padx=5)
            
            tool_btn = ctk.CTkButton(row_frame, text="⚙", width=30, command=lambda tv=type_var, trg=target_var: self.helper_tool(tv, trg))
            tool_btn.pack(side="left", padx=5)
            
            self.bulk_btn_widgets[letter] = {"type": type_var, "target": target_var}
            
        self.save_btn_lbl = ctk.CTkButton(tab_map, text="Save All Buttons", fg_color="#2FA572", hover_color="#238258", command=self.save_all_buttons)
        self.save_btn_lbl.pack(pady=10)

        # --- TAB 3: SLIDER MATRIX ---
        slider_scroll = ctk.CTkScrollableFrame(tab_sliders)
        slider_scroll.pack(fill="both", expand=True, pady=10)
        
        for i in range(1, 7):
            idx_str = str(i)
            row_frame = ctk.CTkFrame(slider_scroll, fg_color="transparent")
            row_frame.pack(fill="x", pady=4)
            
            ctk.CTkLabel(row_frame, text=f"Slider {idx_str}", width=60, anchor="w").pack(side="left", padx=5)
            
            saved_app = self.config["sliders"].get(idx_str, "")
            app_var = ctk.StringVar(value=saved_app)
            ctk.CTkEntry(row_frame, textvariable=app_var, width=280, placeholder_text="'system', 'spotify', 'strip 3', 'bus 0'").pack(side="left", padx=5)
            
            self.bulk_slider_widgets[idx_str] = app_var

        ctk.CTkButton(tab_sliders, text="Save All Sliders", fg_color="#2FA572", hover_color="#238258", command=self.save_all_sliders).pack(pady=10)

        # --- TAB 4 & 5: TEST TABS ---
        grid_frame = ctk.CTkFrame(tab_test_btns, fg_color="transparent")
        grid_frame.pack(pady=20)
        
        for i in range(25):
            letter = chr(65 + i)
            row = i // 5
            col = i % 5
            btn = ctk.CTkButton(grid_frame, text=letter, width=40, height=40, state="disabled", fg_color="#333333")
            btn.grid(row=row, column=col, padx=3, pady=3)
            self.grid_buttons[letter] = btn
            
        z_btn = ctk.CTkButton(grid_frame, text="Z (A0)", width=40, height=40, state="disabled", fg_color="#333333")
        z_btn.grid(row=5, column=2, padx=3, pady=15)
        self.grid_buttons['Z'] = z_btn

        sliders_frame = ctk.CTkFrame(tab_test_sliders, fg_color="transparent")
        sliders_frame.pack(pady=20, fill="x", padx=20)
        
        for i in range(1, 7):
            row_frame = ctk.CTkFrame(sliders_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=10)
            ctk.CTkLabel(row_frame, text=f"Slider {i}", width=50).pack(side="left")
            bar = ctk.CTkProgressBar(row_frame)
            bar.pack(side="left", fill="x", expand=True, padx=10)
            bar.set(0)
            self.slider_bars[str(i)] = bar

    # --- UI Logic ---
    def change_audio_device(self, choice):
        self.config["audio_device"] = choice
        self.save_config()
        self.init_audio_mixer()
        
    def helper_tool(self, type_var, target_var):
        action = type_var.get()
        if action == "Keyboard Shortcut":
            self.active_record_var = target_var
            self.active_record_var.set("Press a key...")
            self.bind("<KeyPress>", self.capture_key)
            self.focus_set()
        elif action == "Soundboard (Audio File)":
            filepath = ctk.filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")])
            if filepath:
                target_var.set(filepath)

    def save_all_buttons(self):
        for letter, widgets in self.bulk_btn_widgets.items():
            self.config["buttons"][letter] = {
                "type": widgets["type"].get(),
                "target": widgets["target"].get()
            }
        self.save_config()
        self.save_btn_lbl.configure(text="Saved successfully!")
        self.after(2000, lambda: self.save_btn_lbl.configure(text="Save All Buttons"))

    def save_all_sliders(self):
        for idx_str, app_var in self.bulk_slider_widgets.items():
            self.config["sliders"][idx_str] = app_var.get().lower().strip()
        self.save_config()

    def capture_key(self, event):
        self.unbind("<KeyPress>")
        if not self.active_record_var: return
        key = event.keysym.lower()
        modifiers = []
        if event.state & 0x0001: modifiers.append('shift')
        if event.state & 0x0004: modifiers.append('ctrl')
        if event.state & 0x20000: modifiers.append('alt')
        if key in ['shift_l', 'shift_r', 'control_l', 'control_r', 'alt_l', 'alt_r', 'windows_l']:
            shortcut = key.split('_')[0]
        else:
            shortcut = "+".join(modifiers + [key]) if modifiers else key
        self.active_record_var.set(shortcut)
        self.active_record_var = None

    def save_connection_settings(self):
        self.config["serial_port"] = self.port_var.get()
        self.config["use_obs"] = self.use_obs_var.get()
        self.config["obs_password"] = self.obs_pass_var.get()
        self.config["autoconnect"] = self.autoconnect_var.get()
        self.save_config()

    # --- Hardware Control Logic ---
    def flash_grid_button(self, btn_id):
        if btn_id in self.grid_buttons:
            btn = self.grid_buttons[btn_id]
            btn.configure(fg_color="#2FA572")
            self.after(200, lambda: btn.configure(fg_color="#333333"))

    def update_slider_ui(self, slider_id, volume):
        if slider_id in self.slider_bars:
            self.slider_bars[slider_id].set(volume / 100.0)

    def set_master_volume(self, volume_percent):
        try:
            CoInitialize()
            
            # Bypass the pycaw wrapper and ask Windows for the raw endpoint directly
            device_enumerator = AudioUtilities.CreateDeviceEnumerator()
            endpoint = device_enumerator.GetDefaultAudioEndpoint(0, 1)
            
            interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            vol_val = max(0.0, min(1.0, volume_percent / 100.0))
            volume.SetMasterVolumeLevelScalar(vol_val, None)
        except Exception as e:
            print(f"Master Volume Error: {e}")

    def set_app_volume(self, app_name, volume_percent):
        try:
            CoInitialize()
            app_target = app_name.lower().replace(".exe", "").strip() + ".exe"
            
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.Process.name():
                    if session.Process.name().lower() == app_target:
                        volume_interface = session._ctl.QueryInterface(ISimpleAudioVolume)
                        vol_val = max(0.0, min(1.0, volume_percent / 100.0))
                        volume_interface.SetMasterVolume(vol_val, None)
        except Exception as e:
            print(f"App Volume Error for {app_name}: {e}")

    def toggle_connection(self):
        if self.is_running:
            self.is_running = False
            if self.arduino: self.arduino.close()
            self.connect_btn.configure(text="Connect")
            self.status_lbl.configure(text="Status: Disconnected", text_color="red")
        else:
            try:
                self.save_connection_settings()
                self.arduino = serial.Serial(self.config["serial_port"], 9600, timeout=1)
                self.arduino.reset_input_buffer()
                
                status_text = f"Connected to {self.config['serial_port']}"
                
                if self.config["use_obs"]:
                    try:
                        self.obs_client = obs.ReqClient(host=self.config["obs_host"], port=self.config["obs_port"], password=self.config["obs_password"])
                        status_text += " & OBS"
                    except Exception as obs_err:
                        status_text += " (OBS Failed)"
                else:
                    self.obs_client = None
                    
                self.is_running = True
                threading.Thread(target=self.serial_listener, daemon=True).start()
                
                self.connect_btn.configure(text="Disconnect")
                self.status_lbl.configure(text=f"Status: {status_text}", text_color="#2FA572")
            except Exception as e:
                self.status_lbl.configure(text=f"Error: {e}", text_color="red")

    def serial_listener(self):
        CoInitialize() 
        
        while self.is_running:
            try:
                pending_sliders = {}
                
                # Drain the buffer entirely to stop the UI from choking
                while self.arduino.in_waiting > 0:
                    data = self.arduino.readline().decode('utf-8').strip()
                    
                    if data.startswith("BTN:"):
                        btn_id = data.split(":")[1]
                        self.after(0, self.flash_grid_button, btn_id)
                        
                        if btn_id in self.config["buttons"]:
                            action = self.config["buttons"][btn_id]
                            
                            # Soundboard
                            if action["type"] == "Soundboard (Audio File)":
                                if os.path.exists(action["target"]):
                                    pygame.mixer.music.load(action["target"])
                                    pygame.mixer.music.play()
                            elif action["type"] == "Stop Soundboard":
                                pygame.mixer.music.stop()
                                    
                            # OBS Smart Scene
                            elif action["type"] == "OBS Smart Scene (Index)" and self.obs_client:
                                try:
                                    target_index = int(action["target"]) - 1
                                    scenes = self.obs_client.get_scene_list().scenes
                                    scenes.reverse()
                                    
                                    if 0 <= target_index < len(scenes):
                                        scene_name = scenes[target_index]['sceneName']
                                        studio_on = self.obs_client.get_studio_mode_enabled().studio_mode_enabled
                                        
                                        if studio_on:
                                            self.obs_client.set_current_preview_scene(scene_name)
                                        else:
                                            self.obs_client.set_current_program_scene(scene_name)
                                except Exception:
                                    pass
                                    
                            # Legacy OBS Commands
                            elif action["type"] == "OBS Scene (Live/Name)" and self.obs_client:
                                self.obs_client.set_current_program_scene(action["target"])
                            elif action["type"] == "OBS Preview (Name)" and self.obs_client:
                                self.obs_client.set_current_preview_scene(action["target"])
                            elif action["type"] == "OBS Transition" and self.obs_client:
                                self.obs_client.trigger_studio_mode_transition()
                                
                            # Keyboard Shortcuts
                            elif action["type"] == "Keyboard Shortcut":
                                keys = [k.strip().lower() for k in action["target"].split('+')]
                                pyautogui.hotkey(*keys)
                                
                    elif data.startswith("SLIDER_"):
                        parts = data.split(":")
                        pending_sliders[parts[0].split("_")[1]] = int(parts[1])
                        
 # Apply batched slider movements once per loop iteration
                for slider_id, raw_volume in pending_sliders.items():
                    # Keep the UI matching your physical slider position
                    self.after(0, self.update_slider_ui, slider_id, raw_volume)
                    
                    if slider_id in self.config["sliders"]:
                        target = self.config["sliders"][slider_id].lower().strip()
                        normalized = raw_volume / 100.0
                        
                        # -- VOICEMEETER CONTROL --
                        if target.startswith("strip ") or target.startswith("bus "):
                            if self.vm:
                                # Cube-root curve: 50% physical slider becomes ~80% logical (-12dB)
                                vm_curve = math.pow(normalized, 0.32) 
                                gain_db = (vm_curve * 60) - 60
                                
                                # Hard mute if pulled all the way down
                                if gain_db < -58: gain_db = -60 
                                
                                try:
                                    parts = target.split(" ")
                                    channel_type = parts[0]
                                    idx = int(parts[1])
                                    
                                    if channel_type == "strip":
                                        self.vm.strip[idx].gain = gain_db
                                    elif channel_type == "bus":
                                        self.vm.bus[idx].gain = gain_db
                                except Exception as e:
                                    print(f"VoiceMeeter Error: {e}")
                                    
                        # -- WINDOWS SYSTEM MASTER --
                        elif target == "system":
                            # Windows handles its own audio taper natively, so we pass it linear
                            self.set_master_volume(raw_volume)
                            
                        # -- SPECIFIC APP VOLUME --
                        elif target != "":
                            self.set_app_volume(target, raw_volume)
                            
            except Exception as e:
                print(f"Listener Error: {e}")
                
            # Forces the thread to wait 20ms, dropping CPU usage and eliminating UI lag
            time.sleep(0.02) 

if __name__ == "__main__":
    app = ModernStreamDeck()
    app.mainloop()
