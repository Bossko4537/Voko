import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread, Event
from time import sleep
from random import uniform
from pynput import mouse, keyboard
import subprocess
import sys
import os

# Auto-install required packages
try:
    from pynput import mouse, keyboard
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    os.execv(sys.executable, [sys.executable] + sys.argv)

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.iconbitmap("logo.ico")
        self.root.geometry("600x430")
        self.root.resizable(False, False)

        # Variables
        self.click_key = None
        self.start_stop_key = keyboard.Key.f5
        self.recording_click = False
        self.recording_hotkey = False
        self.interval = {'hours': 0, 'minutes': 0, 'seconds': 0, 'ms': 100}
        self.mode = tk.StringVar(value="Click")
        self.repeat_mode = tk.StringVar(value="until_stopped")
        self.repeat_times = tk.IntVar(value=10)
        self.always_on_top = tk.BooleanVar(value=True)
        self.block_on_ui = tk.BooleanVar(value=True)
        self.theme = tk.StringVar(value="Default")

        # Humanoid
        self.humanoid = tk.BooleanVar(value=False)
        self.humanoid_min = tk.StringVar(value="0.1")
        self.humanoid_max = tk.StringVar(value="0.3")

        self.stop_event = Event()
        self.running = False

        self.k_controller = keyboard.Controller()
        self.m_controller = mouse.Controller()

        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()
        self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        self.mouse_listener.start()

        self.build_ui()
        self.apply_theme()
        self.toggle_topmost()

    def build_ui(self):
        key_frame = tk.Frame(self.root)
        key_frame.pack(pady=10)

        tk.Label(key_frame, text="Click Key:").grid(row=0, column=0, padx=5)
        self.click_key_label = tk.Label(key_frame, text="None")
        self.click_key_label.grid(row=0, column=1)
        tk.Button(key_frame, text="Record", command=self.record_click_key).grid(row=0, column=2, padx=10)

        tk.Label(key_frame, text="Start/Stop Key:").grid(row=0, column=3, padx=5)
        self.hotkey_label = tk.Label(key_frame, text=self.key_to_string(self.start_stop_key))
        self.hotkey_label.grid(row=0, column=4)
        tk.Button(key_frame, text="Record", command=self.record_hotkey).grid(row=0, column=5, padx=10)

        self.recording_label = tk.Label(self.root, text="", fg="red")
        self.recording_label.pack()

        mode_frame = tk.Frame(self.root)
        mode_frame.pack(pady=5)
        ttk.Label(mode_frame, text="Mode:").grid(row=0, column=0)
        ttk.OptionMenu(mode_frame, self.mode, "Click", "Click", "Hold").grid(row=0, column=1, padx=10)

        ttk.Label(mode_frame, text="Repeat:").grid(row=0, column=2)
        ttk.Radiobutton(mode_frame, text="Until stopped", variable=self.repeat_mode, value="until_stopped").grid(row=0, column=3)
        ttk.Radiobutton(mode_frame, text="Set times", variable=self.repeat_mode, value="set_times").grid(row=0, column=4)
        tk.Entry(mode_frame, textvariable=self.repeat_times, width=5).grid(row=0, column=5)

        self.interval_frame = tk.Frame(self.root)
        self.interval_frame.pack(pady=5)

        self.entries = {}
        for i, (label, unit) in enumerate([("Hours", "hours"), ("Minutes", "minutes"), ("Seconds", "seconds"), ("Milliseconds", "ms")]):
            tk.Label(self.interval_frame, text=label).grid(row=0, column=i*2)
            entry = tk.Entry(self.interval_frame, width=5)
            entry.insert(0, "0" if unit != "ms" else str(self.interval['ms']))
            entry.grid(row=0, column=i*2+1)
            entry.bind("<FocusOut>", lambda e, u=unit: self.validate_interval(u))
            entry.bind("<Return>", lambda e, u=unit: self.validate_interval(u))
            self.entries[unit] = entry

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(btn_frame, text="Start", command=self.start_clicking)
        self.start_btn.grid(row=0, column=0, padx=10)
        self.stop_btn = tk.Button(btn_frame, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=10)

        extra = tk.LabelFrame(self.root, text="Extra Settings")
        extra.pack(fill="x", padx=10, pady=10)

        tk.Checkbutton(extra, text="Stop if UI interacted with", variable=self.block_on_ui).pack(anchor="w", padx=10)
        tk.Checkbutton(extra, text="Always on top", variable=self.always_on_top, command=self.toggle_topmost).pack(anchor="w", padx=10)

        tk.Checkbutton(extra, text="Humanoid (random delay)", variable=self.humanoid, command=self.toggle_humanoid).pack(anchor="w", padx=10)

        humanoid_frame = tk.Frame(extra)
        humanoid_frame.pack(anchor="w", padx=20)
        tk.Label(humanoid_frame, text="Min Delay (s):").grid(row=0, column=0, sticky="w")
        self.h_min = tk.Entry(humanoid_frame, width=6, textvariable=self.humanoid_min)
        self.h_min.grid(row=0, column=1)

        tk.Label(humanoid_frame, text="Max Delay (s):").grid(row=0, column=2, padx=(10, 0))
        self.h_max = tk.Entry(humanoid_frame, width=6, textvariable=self.humanoid_max)
        self.h_max.grid(row=0, column=3)

        tk.Label(extra, text="Theme:").pack(anchor="w", padx=10, pady=(5, 0))
        theme_menu = ttk.OptionMenu(
            extra, self.theme, self.theme.get(),
            "Default", "Black", "Blue", "Light Pink", "Red", "Green",
            "Purple", "Yellow", "Orange", "White", "Gray",
            command=lambda _: self.apply_theme()
        )
        theme_menu.pack(anchor="w", padx=10)

        self.toggle_humanoid()

    def toggle_humanoid(self):
        state = "disabled" if self.humanoid.get() else "normal"
        for entry in self.entries.values():
            entry.configure(state=state)
        self.h_min.configure(state="normal" if self.humanoid.get() else "disabled")
        self.h_max.configure(state="normal" if self.humanoid.get() else "disabled")

    def validate_interval(self, unit):
        value = self.entries[unit].get()
        if not value.isdigit():
            self.entries[unit].delete(0, tk.END)
            self.entries[unit].insert(0, "0")
        else:
            value = int(value)
            if unit == "ms" or value > 0:
                self.interval[unit] = value
                if unit != "ms" and str(value).startswith("0") and len(str(value)) > 1:
                    self.entries[unit].delete(0, tk.END)
                    self.entries[unit].insert(0, str(int(value)))
            else:
                self.entries[unit].delete(0, tk.END)
                self.entries[unit].insert(0, "0")

    def record_click_key(self):
        if self.recording_hotkey:
            return
        self.recording_click = True
        self.recording_label.config(text="Recording Click Key...")

    def record_hotkey(self):
        if self.recording_click:
            return
        self.recording_hotkey = True
        self.recording_label.config(text="Recording Hotkey...")

    def on_mouse_click(self, x, y, button, pressed):
        if not pressed or not self.recording_click:
            return
        if button in [mouse.Button.left, mouse.Button.right, mouse.Button.middle]:
            self.click_key = button
            self.click_key_label.config(text=f"Button.{button.name}")
            self.recording_click = False
            self.recording_label.config(text="")

    def on_key_press(self, key):
        if self.recording_click:
            self.click_key = key
            self.click_key_label.config(text=self.key_to_string(key))
            self.recording_click = False
            self.recording_label.config(text="")
        elif self.recording_hotkey:
            self.start_stop_key = key
            self.hotkey_label.config(text=self.key_to_string(key))
            self.recording_hotkey = False
            self.recording_label.config(text="")
        elif key == self.start_stop_key:
            if self.running:
                self.stop_clicking()
            else:
                self.start_clicking()

    def key_to_string(self, key):
        if isinstance(key, keyboard.KeyCode):
            return key.char if key.char else str(key)
        elif isinstance(key, keyboard.Key):
            return str(key).replace("Key.", "Key.")
        elif isinstance(key, mouse.Button):
            return f"Button.{key.name}"
        else:
            return str(key)

    def start_clicking(self):
        if not self.click_key:
            messagebox.showerror("Missing Click Key", "Please record a Click Key first.")
            return
        if not self.humanoid.get():
            for unit in self.interval:
                self.validate_interval(unit)
        else:
            try:
                min_delay = float(self.humanoid_min.get())
                max_delay = float(self.humanoid_max.get())
                if min_delay < 0 or max_delay <= min_delay:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Humanoid Delay Error", "Min must be >= 0 and Max must be > Min.")
                return

        self.stop_event.clear()
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.set_ui_state(disabled=True)
        self.toggle_topmost()
        Thread(target=self.run_clicker, daemon=True).start()

    def stop_clicking(self):
        self.stop_event.set()
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.set_ui_state(disabled=False)
        self.toggle_topmost()

    def set_ui_state(self, disabled):
        state = "disabled" if disabled else "normal"
        for child in self.root.winfo_children():
            if isinstance(child, tk.Button) and child != self.stop_btn:
                child.config(state=state)
            elif isinstance(child, tk.Entry):
                child.config(state=state)

    def run_clicker(self):
        total = 0
        if self.humanoid.get():
            get_delay = lambda: uniform(float(self.humanoid_min.get()), float(self.humanoid_max.get()))
        else:
            fixed_delay = (
                self.interval['hours'] * 3600
                + self.interval['minutes'] * 60
                + self.interval['seconds']
                + self.interval['ms'] / 1000
            )
            get_delay = lambda: fixed_delay

        while not self.stop_event.is_set():
            if self.block_on_ui.get() and self.root.focus_displayof():
                self.stop_clicking()
                return

            if isinstance(self.click_key, mouse.Button):
                if self.mode.get() == "Click":
                    self.m_controller.click(self.click_key, 1)
                elif self.mode.get() == "Hold":
                    self.m_controller.press(self.click_key)
                    sleep(get_delay() / 2)
                    self.m_controller.release(self.click_key)
            else:
                if self.mode.get() == "Click":
                    self.k_controller.press(self.click_key)
                    self.k_controller.release(self.click_key)
                elif self.mode.get() == "Hold":
                    self.k_controller.press(self.click_key)
                    sleep(get_delay() / 2)
                    self.k_controller.release(self.click_key)

            total += 1
            if self.repeat_mode.get() == "set_times" and total >= self.repeat_times.get():
                break
            sleep(get_delay())

        self.stop_clicking()

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.always_on_top.get() and not self.running)

    def apply_theme(self):
        theme_colors = {
            "Default": {"bg": "#cccccc"},
            "Black": {"bg": "#000000"},
            "Blue": {"bg": "#0066cc"},
            "Light Pink": {"bg": "#ffc0cb"},
            "Red": {"bg": "#cc0000"},
            "Green": {"bg": "#00aa00"},
            "Purple": {"bg": "#800080"},
            "Yellow": {"bg": "#ffff99"},
            "Orange": {"bg": "#ff9900"},
            "White": {"bg": "#ffffff"},
            "Gray": {"bg": "#888888"},
        }

        selected_theme = self.theme.get()
        theme = theme_colors.get(selected_theme, theme_colors["Default"])
        bg = theme["bg"]

        def brightness(hex_color):
            hex_color = hex_color.lstrip("#")
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return (r * 299 + g * 587 + b * 114) / 1000

        fg = "#000000" if brightness(bg) > 128 else "#ffffff"

        self.root.configure(bg=bg)

        for w in self.root.winfo_children():
            self._apply_theme_recursive(w, bg, fg)

    def _apply_theme_recursive(self, widget, bg, fg):
        if isinstance(widget, (tk.Label, tk.Checkbutton, tk.Radiobutton, tk.LabelFrame)):
            widget.configure(bg=bg, fg=fg)
        elif isinstance(widget, tk.Button):
            widget.configure(fg=fg)
        elif isinstance(widget, tk.Entry):
            widget.configure(fg=fg, insertbackground=fg)
        elif isinstance(widget, ttk.OptionMenu):
            widget.configure(style='TMenubutton')
        for child in widget.winfo_children():
            self._apply_theme_recursive(child, bg, fg)

# Launch
if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
