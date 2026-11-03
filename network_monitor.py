import json
import os
import socket
import subprocess
import threading
import time
import tkinter as tk
from tkinter import colorchooser, messagebox
import psutil

APP_NAME = "Network Monitor Pro"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NetworkMonitorPro")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

DEFAULTS = {
    "bg": "#171923",
    "fg": "#F7FAFC",
    "accent": "#63B3ED",
    "font_size": 11,
    "width": 245,
    "height": 180,
    "speed_unit": "Auto",
    "alpha": 0.92,
    "show_download": True,
    "show_upload": True,
    "show_ping": True,
    "show_status": True,
    "always_on_top": True,
    "refresh_ms": 1000,
    "x": None,
    "y": None
}

def load_settings():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        result = DEFAULTS.copy()
        result.update({k: v for k, v in saved.items() if k in DEFAULTS})
        return result
    except Exception:
        return DEFAULTS.copy()

def save_settings(settings):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

def ping_ms():
    host = "1.1.1.1"
    try:
        flag = "-n" if os.name == "nt" else "-c"
        result = subprocess.run(
            ["ping", flag, "1", "-w", "1500", host],
            capture_output=True, text=True, timeout=2.5
        )
        output = result.stdout
        import re
        match = re.search(r"time[=<]\s*([\d.]+)\s*ms", output, re.I)
        if match:
            return f"{float(match.group(1)):.0f} ms"
        match = re.search(r"time[=<]\s*([\d.]+)\s*ms", result.stderr, re.I)
        return f"{float(match.group(1)):.0f} ms" if match else "N/A"
    except Exception:
        return "N/A"

class NetworkMonitor:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.last = psutil.net_io_counters()
        self.last_time = time.monotonic()
        self.down = 0.0
        self.up = 0.0
        self.ping = "..."
        self.connected = self.check_connection()
        self.drag = None
        self.settings_window = None

        root.title(APP_NAME)
        root.overrideredirect(True)
        root.configure(bg=self.settings["bg"])
        root.attributes("-topmost", self.settings["always_on_top"])
        self.apply_alpha()
        self.build_ui()
        self.place_window()
        self.bind_drag(self.panel)
        self.refresh()
        self.start_ping_loop()
        root.protocol("WM_DELETE_WINDOW", self.quit)

    def check_connection(self):
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=1.2).close()
            return True
        except OSError:
            return False

    def apply_alpha(self):
        try:
            self.root.attributes("-alpha", float(self.settings["alpha"]))
        except Exception:
            pass

    def place_window(self):
        self.root.update_idletasks()
        x, y = self.settings.get("x"), self.settings.get("y")
        width = int(self.settings.get("width", DEFAULTS["width"]))
        height = int(self.settings.get("height", DEFAULTS["height"]))
        if isinstance(x, int) and isinstance(y, int):
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.root.geometry(f"{width}x{height}+{max(0, sw-width-25)}+{max(0, sh-height-80)}")

    def build_ui(self):
        s = self.settings
        # Scale the complete widget layout (not only the text) to the selected dimensions.
        scale = max(0.65, min(1.45, min(s["width"] / 245, s["height"] / 180)))
        self.ui_scale = scale
        self.panel = tk.Frame(self.root, bg=s["bg"], bd=1, relief="solid",
                              highlightthickness=1, highlightbackground=s["accent"])
        self.panel.pack(fill="both", expand=True)
        top = tk.Frame(self.panel, bg=s["bg"])
        top.pack(fill="x", padx=max(4, int(9*scale)), pady=(max(2, int(5*scale)), 1))
        self.title_label = tk.Label(top, text="NETWORK MONITOR", bg=s["bg"], fg=s["accent"],
                                    font=("Segoe UI", max(7, int((s["font_size"]-2)*scale)), "bold"))
        self.title_label.pack(side="left")
        tk.Button(top, text="⚙", command=self.open_settings, bg=s["bg"], fg=s["fg"],
                  activebackground=s["accent"], activeforeground="#000000",
                  bd=0, padx=max(2, int(5*scale)), font=("Segoe UI", max(8, int(10*scale))), cursor="hand2").pack(side="right")
        tk.Button(top, text="×", command=self.quit, bg=s["bg"], fg=s["fg"],
                  activebackground="#E53E3E", activeforeground="white",
                  bd=0, padx=max(2, int(5*scale)), font=("Segoe UI", max(8, int(12*scale)), "bold"), cursor="hand2").pack(side="right")

        self.labels = {}
        self.make_line("download", "↓ Download", self.format_speed(0))
        self.make_line("upload", "↑ Upload", self.format_speed(0))
        self.make_line("ping", "◉ Ping", "...")
        self.make_line("status", "● Status", "Checking")
        self.apply_visibility()

        hint = tk.Label(self.panel, text="Drag to move • ⚙ Settings", bg=s["bg"],
                        fg="#A0AEC0", font=("Segoe UI", max(6, int(8*scale))))
        hint.pack(anchor="e", padx=max(4, int(9*scale)), pady=(0, max(2, int(5*scale))))

    def make_line(self, key, caption, initial):
        scale = self.ui_scale
        row = tk.Frame(self.panel, bg=self.settings["bg"])
        row.pack(fill="x", padx=max(4, int(10*scale)), pady=max(0, int(2*scale)))
        left = tk.Label(row, text=caption, bg=self.settings["bg"], fg=self.settings["fg"],
                        font=("Segoe UI", max(7, int(self.settings["font_size"]*scale))))
        left.pack(side="left")
        right = tk.Label(row, text=initial, bg=self.settings["bg"], fg=self.settings["accent"],
                         font=("Segoe UI", max(7, int(self.settings["font_size"]*scale)), "bold"))
        right.pack(side="right")
        self.labels[key] = (row, left, right)

    def apply_visibility(self):
        for key, (row, _, _) in self.labels.items():
            if self.settings.get("show_" + key, True):
                row.pack(fill="x", padx=10, pady=2)
            else:
                row.pack_forget()

    def bind_drag(self, widget):
        for w in (widget, self.panel):
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.do_drag)
            w.bind("<ButtonRelease-1>", self.end_drag)

    def start_drag(self, event):
        self.drag = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def do_drag(self, event):
        if self.drag:
            x, y = event.x_root - self.drag[0], event.y_root - self.drag[1]
            self.root.geometry(f"+{x}+{y}")

    def end_drag(self, event):
        self.settings["x"], self.settings["y"] = self.root.winfo_x(), self.root.winfo_y()
        save_settings(self.settings)

    def format_speed(self, bytes_per_second):
        unit = self.settings.get("speed_unit", "Auto")
        if unit == "KB/s":
            return f"{bytes_per_second / 1024:.1f} KB/s"
        if unit == "MB/s":
            return f"{bytes_per_second / (1024 * 1024):.2f} MB/s"
        if bytes_per_second >= 1024 * 1024:
            return f"{bytes_per_second / (1024 * 1024):.2f} MB/s"
        return f"{bytes_per_second / 1024:.1f} KB/s"

    def refresh(self):
        now = time.monotonic()
        counters = psutil.net_io_counters()
        elapsed = max(now - self.last_time, 0.001)
        self.down = max(0, counters.bytes_recv - self.last.bytes_recv) / elapsed
        self.up = max(0, counters.bytes_sent - self.last.bytes_sent) / elapsed
        self.last, self.last_time = counters, now
        self.labels["download"][2].config(text=self.format_speed(self.down))
        self.labels["upload"][2].config(text=self.format_speed(self.up))
        self.labels["ping"][2].config(text=self.ping)
        online = self.check_connection()
        self.labels["status"][2].config(
            text="Online" if online else "Offline",
            fg="#48BB78" if online else "#F56565"
        )
        self.root.after(int(self.settings["refresh_ms"]), self.refresh)

    def start_ping_loop(self):
        def worker():
            while True:
                self.ping = ping_ms()
                time.sleep(5)
        threading.Thread(target=worker, daemon=True).start()

    def open_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        win = tk.Toplevel(self.root)
        self.settings_window = win
        win.title("Network Monitor Settings")
        win.geometry("380x690")
        win.resizable(False, False)
        win.configure(bg="#F7FAFC")
        win.attributes("-topmost", True)
        outer = tk.Frame(win, bg="#F7FAFC", padx=16, pady=12)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="Display settings", bg="#F7FAFC", fg="#1A202C",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 10))

        def section(text):
            tk.Label(outer, text=text, bg="#F7FAFC", fg="#4A5568",
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(9, 3))

        section("SIZE & TRANSPARENCY")
        self.add_scale(outer, "Width (px)", "width", 150, 500, 5)
        self.add_scale(outer, "Height (px)", "height", 125, 420, 5)
        self.add_scale(outer, "Font size", "font_size", 8, 20, 1)
        section("SPEED UNIT")
        self.unit_var = tk.StringVar(value=self.settings.get("speed_unit", "Auto"))
        unit_menu = tk.OptionMenu(outer, self.unit_var, "Auto", "KB/s", "MB/s")
        unit_menu.config(bg="#E2E8F0", fg="#2D3748", bd=0, highlightthickness=0,
                         activebackground="#CBD5E0", width=12)
        unit_menu.pack(anchor="w")
        self.add_scale(outer, "Transparency", "alpha_percent", 35, 100, 5,
                       initial=int(self.settings["alpha"]*100))

        section("COLORS")
        colors = tk.Frame(outer, bg="#F7FAFC")
        colors.pack(fill="x")
        tk.Button(colors, text="Background color", command=lambda: self.pick_color("bg"),
                  bg="#E2E8F0", bd=0, padx=10, pady=6).pack(side="left", padx=(0, 7))
        tk.Button(colors, text="Text color", command=lambda: self.pick_color("fg"),
                  bg="#E2E8F0", bd=0, padx=10, pady=6).pack(side="left")

        section("SHOW / HIDE")
        self.vars = {}
        for key, label in [("download", "Download speed"), ("upload", "Upload speed"),
                           ("ping", "Ping"), ("status", "Connection status")]:
            var = tk.BooleanVar(value=self.settings["show_"+key])
            self.vars[key] = var
            tk.Checkbutton(outer, text=label, variable=var, bg="#F7FAFC",
                           activebackground="#F7FAFC", fg="#2D3748").pack(anchor="w")

        self.top_var = tk.BooleanVar(value=self.settings["always_on_top"])
        tk.Checkbutton(outer, text="Always on top", variable=self.top_var, bg="#F7FAFC",
                       activebackground="#F7FAFC", fg="#2D3748").pack(anchor="w", pady=(5, 0))

        buttons = tk.Frame(outer, bg="#F7FAFC")
        buttons.pack(fill="x", side="bottom", pady=(14, 0))
        tk.Button(buttons, text="Save settings", command=self.save_from_settings,
                  bg="#3182CE", fg="white", activebackground="#2B6CB0",
                  bd=0, padx=12, pady=8).pack(side="left", expand=True, fill="x", padx=(0, 5))
        tk.Button(buttons, text="Reset", command=self.reset_settings,
                  bg="#E2E8F0", fg="#2D3748", bd=0, padx=12, pady=8).pack(side="left")

    def add_scale(self, parent, label, key, low, high, resolution, initial=None):
        frame = tk.Frame(parent, bg="#F7FAFC")
        frame.pack(fill="x")
        tk.Label(frame, text=label, bg="#F7FAFC", fg="#2D3748").pack(anchor="w")
        value = initial if initial is not None else self.settings[key]
        var = tk.IntVar(value=int(value))
        setattr(self, "scale_"+key, var)
        tk.Scale(frame, from_=low, to=high, resolution=resolution, orient="horizontal",
                 variable=var, showvalue=True, bg="#F7FAFC", highlightthickness=0,
                 troughcolor="#CBD5E0", length=310).pack(fill="x")

    def pick_color(self, key):
        chosen = colorchooser.askcolor(color=self.settings[key], title="Choose color")[1]
        if chosen:
            self.settings[key] = chosen

    def save_from_settings(self):
        self.settings["width"] = self.scale_width.get()
        self.settings["height"] = self.scale_height.get()
        self.settings["speed_unit"] = self.unit_var.get()
        self.settings["font_size"] = self.scale_font_size.get()
        self.settings["alpha"] = self.scale_alpha_percent.get()/100
        for key, var in self.vars.items():
            self.settings["show_"+key] = var.get()
        self.settings["always_on_top"] = self.top_var.get()
        save_settings(self.settings)
        self.root.attributes("-topmost", self.settings["always_on_top"])
        self.apply_alpha()
        self.rebuild()
        messagebox.showinfo("Saved", "Settings saved successfully. Changes applied.")

    def reset_settings(self):
        if not messagebox.askyesno("Reset", "Restore all settings to default?"):
            return
        pos = (self.root.winfo_x(), self.root.winfo_y())
        self.settings = DEFAULTS.copy()
        self.settings["x"], self.settings["y"] = pos
        save_settings(self.settings)
        self.apply_alpha()
        self.root.attributes("-topmost", True)
        self.rebuild()
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None

    def rebuild(self):
        for child in self.root.winfo_children():
            child.destroy()
        self.root.configure(bg=self.settings["bg"])
        self.build_ui()
        self.bind_drag(self.panel)
        self.root.geometry(f'{self.settings["width"]}x{self.settings["height"]}+{self.root.winfo_x()}+{self.root.winfo_y()}')
        self.apply_alpha()

    def quit(self):
        try:
            self.settings["x"], self.settings["y"] = self.root.winfo_x(), self.root.winfo_y()
            save_settings(self.settings)
        except Exception:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkMonitor(root)
    root.mainloop()
