import tkinter as tk
from tkinter import messagebox
import socket
import struct
import threading
import time
import math
import os
import random

# CAN Configuration
CAN_INTERFACE = "vcan0"
CAN_ID_SPEED = 0x244
CAN_ID_DOORS = 0x19B

class VehicleDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("CANSentinel // DIGITAL CLUSTER")
        self.root.geometry("800x450")
        self.root.configure(bg="#050505")

        self.sock = None
        self.running = True
        
        # Physics State
        self.current_speed = 0
        self.current_rpm = 0
        self.target_speed = 0
        self.gear = 1
        self.engine_on = False
        
        # Door State
        self.doors_locked = True
        
        # IDS State
        self.last_packet_time = 0
        self.ids_alert = False

        self.setup_ui()
        self.setup_can()
        
        threading.Thread(target=self.can_listener, daemon=True).start()
        threading.Thread(target=self.engine_loop, daemon=True).start()

    def setup_ui(self):
        # 1. Header
        self.header = tk.Label(self.root, text="::: SPORT MODE ACTIVE :::", font=("Eurostile", 14), fg="#555", bg="#050505")
        self.header.pack(pady=10)

        # 2. Cluster Frame (RPM | Status | Speed)
        cluster = tk.Frame(self.root, bg="#050505")
        cluster.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # RPM Gauge (Left)
        frame_rpm = tk.Frame(cluster, bg="#050505")
        frame_rpm.pack(side=tk.LEFT, expand=True)
        self.canvas_rpm = tk.Canvas(frame_rpm, width=250, height=250, bg="#050505", highlightthickness=0)
        self.canvas_rpm.pack()
        self.draw_rpm_bg()
        self.lbl_rpm = tk.Label(frame_rpm, text="0 RPM", font=("Consolas", 16, "bold"), fg="#ffaa00", bg="#050505")
        self.lbl_rpm.pack()
        
        # Status Center
        self.frame_center = tk.Frame(cluster, bg="#050505")
        self.frame_center.pack(side=tk.LEFT, padx=10)
        
        self.lbl_gear = tk.Label(self.frame_center, text="N", font=("Arial", 40, "bold"), fg="#aaa", bg="#050505")
        self.lbl_gear.pack(pady=10)
        
        # Door Indicator
        self.lbl_door = tk.Label(self.frame_center, text="[ DOORS LOCKED ]", font=("Consolas", 12), fg="#00ff00", bg="#050505")
        self.lbl_door.pack(pady=5)
        
        self.lbl_ids = tk.Label(self.frame_center, text="SYSTEM\nSECURE", font=("Impact", 18), fg="#004400", bg="#050505")
        self.lbl_ids.pack(pady=20)

        # Speed Gauge (Right)
        frame_speed = tk.Frame(cluster, bg="#050505")
        frame_speed.pack(side=tk.RIGHT, expand=True)
        self.canvas_speed = tk.Canvas(frame_speed, width=250, height=250, bg="#050505", highlightthickness=0)
        self.canvas_speed.pack()
        self.draw_speed_bg()
        self.lbl_speed = tk.Label(frame_speed, text="0 KM/H", font=("Consolas", 16, "bold"), fg="#00ccff", bg="#050505")
        self.lbl_speed.pack()

        # 3. Controls
        frame_controls = tk.Frame(self.root, bg="#111", pady=10)
        frame_controls.pack(fill=tk.X)
        
        btn_engine = tk.Button(frame_controls, text="START / STOP ENGINE", bg="#005500", fg="white", 
                               command=self.toggle_engine, font=("Consolas", 10, "bold"))
        btn_engine.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
        
        # Door Control
        self.btn_door = tk.Button(frame_controls, text="UNLOCK DOORS", bg="#555500", fg="white",
                                 command=self.toggle_doors, font=("Consolas", 10, "bold"))
        self.btn_door.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
        
        btn_hack = tk.Button(frame_controls, text="INJECT MALICIOUS FRAMES", bg="#aa0000", fg="white", 
                             command=self.inject_attack, font=("Consolas", 10, "bold"))
        btn_hack.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)

        # Draw initial needles
        self.needle_rpm = self.draw_needle(self.canvas_rpm, 0, 8000, 240, -60, "orange")
        self.needle_speed = self.draw_needle(self.canvas_speed, 0, 240, 240, -60, "cyan")

    def draw_speed_bg(self):
        self.canvas_speed.create_arc(25, 25, 225, 225, start=-60, extent=300, style=tk.ARC, outline="#333", width=10)
        self.canvas_speed.create_arc(25, 25, 225, 225, start=-60, extent=240, style=tk.ARC, outline="#00ccff", width=3)
        self.canvas_speed.create_text(125, 180, text="KM/H", fill="#555", font=("Arial", 10))

    def draw_rpm_bg(self):
        self.canvas_rpm.create_arc(25, 25, 225, 225, start=-60, extent=300, style=tk.ARC, outline="#333", width=10)
        self.canvas_rpm.create_arc(25, 25, 225, 225, start=-60, extent=200, style=tk.ARC, outline="#ffaa00", width=3)
        self.canvas_rpm.create_arc(25, 25, 225, 225, start=-60, extent=40, style=tk.ARC, outline="red", width=3) # Redline
        self.canvas_rpm.create_text(125, 180, text="RPM x1000", fill="#555", font=("Arial", 10))

    def draw_needle(self, canvas, val, max_val, start_angle, end_angle, color):
        # Calculate angle
        pct = val / max_val
        angle_span = start_angle - end_angle
        angle_deg = start_angle - (pct * angle_span)
        angle_rad = math.radians(angle_deg)
        
        cx, cy = 125, 125
        len_needle = 90
        
        x = cx + len_needle * math.cos(angle_rad)
        y = cy - len_needle * math.sin(angle_rad)
        
        return canvas.create_line(cx, cy, x, y, fill=color, width=4, capstyle=tk.ROUND)

    def update_gauge(self, canvas, needle_id, val, max_val, color):
        pct = min(max(val / max_val, 0), 1.1)
        angle_deg = 240 - (pct * 300) # Span 300 degrees
        angle_rad = math.radians(angle_deg)
        cx, cy = 125, 125
        len_needle = 90
        x = cx + len_needle * math.cos(angle_rad)
        y = cy - len_needle * math.sin(angle_rad)
        canvas.coords(needle_id, cx, cy, x, y)

    def setup_can(self):
        try:
            s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
            s.bind((CAN_INTERFACE,))
            self.sock = s
        except Exception:
            pass # Demo mode if failed

    def can_listener(self):
        while self.running and self.sock:
            try:
                cf, _ = self.sock.recvfrom(16)
                can_id, _, data = struct.unpack("=IB3x8s", cf)
                can_id &= 0x1FFFFFFF 
                
                if can_id == CAN_ID_SPEED:
                    # IDS Check (Flood)
                    now = time.time()
                    if (now - self.last_packet_time) < 0.005: self.trigger_ids("FLOOD DETECTED")
                    else: self.clear_ids()
                    self.last_packet_time = now

                    # Parse Speed
                    speed = struct.unpack(">H", data[0:2])[0] / 100.0
                    self.root.after(0, lambda s=speed: self.update_dashboard(s))
                
                elif can_id == CAN_ID_DOORS:
                    # Door Status: Byte 0 (0=Locked, 1=Open)
                    status = data[0]
                    self.root.after(0, lambda st=status: self.update_doors(st))
                    
                    # IDS Rule: Safety Violation (Moving + Open)
                    # We need current speed. self.current_speed is roughly accurate or we parse from last packet
                    if status == 1 and self.current_speed > 5:
                        self.trigger_ids("SAFETY VIOLATION\nDOOR OPEN WHILE MOVING")

            except Exception: pass

    def engine_loop(self):
        while self.running:
            if self.engine_on:
                # Physics
                if self.current_speed < self.target_speed: self.current_speed += 0.5
                elif self.current_speed > self.target_speed: self.current_speed -= 0.5
                
                self.gear = min(int(self.current_speed / 40) + 1, 6)
                base_rpm = (self.current_speed % 40) * 100 + 1000 + random.randint(-50, 50)
                self.current_rpm = base_rpm
                
                # Broadcast Speed
                raw = int(self.current_speed * 100)
                data = struct.pack(">H", raw) + b'\x00'*6
                self.send_frame(CAN_ID_SPEED, data)
                
                # Random traffic
                if random.random() < 0.05: self.target_speed = random.randint(0, 200)
            
            time.sleep(0.05)

    def update_dashboard(self, speed):
        self.update_gauge(self.canvas_speed, self.needle_speed, speed, 240, "#00ccff")
        self.lbl_speed.config(text=f"{int(speed)} KM/H")
        rpm = self.current_rpm
        self.update_gauge(self.canvas_rpm, self.needle_rpm, rpm, 8000, "orange")
        self.lbl_rpm.config(text=f"{int(rpm)} RPM")
        self.lbl_gear.config(text=str(self.gear))

    def update_doors(self, status):
        if status == 1:
            self.doors_locked = False
            self.lbl_door.config(text="[ DOOR OPEN ]", fg="red")
            self.btn_door.config(text="LOCK DOORS", bg="#550000")
        else:
            self.doors_locked = True
            self.lbl_door.config(text="[ DOORS LOCKED ]", fg="#00ff00")
            self.btn_door.config(text="UNLOCK DOORS", bg="#555500")

    def toggle_doors(self):
        # We act as the Door Controller broadcasting change
        new_status = 1 if self.doors_locked else 0
        data = struct.pack("B", new_status) + b'\x00'*7
        self.send_frame(CAN_ID_DOORS, data)
        # Note: can_listener will pick this up and update UI + Check IDS

    def send_frame(self, can_id, data):
        if self.sock:
            try:
                frame = struct.pack("=IB3x8s", can_id, 8, data.ljust(8, b'\x00'))
                self.sock.send(frame)
            except: pass

    def toggle_engine(self):
        self.engine_on = not self.engine_on
        if self.engine_on: 
            self.lbl_gear.config(fg="#00ccff")
            self.target_speed = 50
        else:
            self.lbl_gear.config(text="N", fg="#aaa")
            self.current_speed = 0
            self.current_rpm = 0
            self.target_speed = 0
            self.update_dashboard(0)
    
    def inject_attack(self):
        threading.Thread(target=self._attack_thread, daemon=True).start()

    def _attack_thread(self):
        raw = int(250 * 100)
        data = struct.pack(">H", raw) + b'\x00'*6
        for _ in range(50):
            self.send_frame(CAN_ID_SPEED, data)
            time.sleep(0.001)

    def trigger_ids(self, msg="INJECTION DETECTED"):
        if not self.ids_alert:
            self.ids_alert = True
            self.root.after(0, lambda: self._show_alert(msg))

    def _show_alert(self, msg):
        self.root.configure(bg="#330000")
        self.lbl_ids.config(text=f"!!! IDS ALERT !!!\n{msg}", fg="white", bg="#aa0000")
        self.lbl_gear.config(text="ERR", fg="red", bg="#330000")

    def clear_ids(self):
        if self.ids_alert:
            self.ids_alert = False
            self.root.after(0, self._clear_alert)

    def _clear_alert(self):
        self.root.configure(bg="#050505")
        self.lbl_ids.config(text="SYSTEM\nSECURE", fg="#004400", bg="#050505")
        self.lbl_gear.config(bg="#050505", text=str(self.gear))

    def on_close(self):
        self.running = False
        if self.sock: self.sock.close()
        self.root.destroy()

if __name__ == "__main__":
    if os.system("ip link show vcan0 > /dev/null 2>&1") != 0:
        print("vcan0 not found! Run: sudo modprobe vcan && sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0")
        exit(1)
    root = tk.Tk()
    app = VehicleDashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
