import tkinter as tk
from tkinter import messagebox, simpledialog
import qrcode # pip install qrcode[pil]
from PIL import Image, ImageTk # pip install pillow
import uuid
import requests # pip install requests
import time
import socket
import threading
import json
import os
import sys
import re as _re
import random
import subprocess
import ctypes
from datetime import datetime

# Set AppUserModelID supaya Windows guna ikon app, bukan ikon Python
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HelmiSoftTech.LabSentinel.Client.1")
except:
    pass

# --- CONFIGURATION ---
CONFIG_FILE = "config.json"
SESSION_TIME_LIMIT = 3 * 60 * 60  # 3 jam dalam saat (10800 saat)

class LockScreenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LabSentinel Client")
        
        # Load Config
        self.config = self.load_config()
        self.server_url = self.config.get("server_url", "http://localhost")
        self.api_url = f"{self.server_url}/api.php"
        self.unlock_url_base = f"{self.server_url}/unlock.php"
        
        self.pc_name = self.config.get("pc_name", socket.gethostname())
        self.lab_name = self.config.get("lab_name", "General Lab")
        self.admin_password = self.config.get("admin_password", "admin")
        
        self.session_uuid = str(uuid.uuid4())
        self.is_unlocked = False
        self.remaining_time = SESSION_TIME_LIMIT  # Masa berbaki dalam saat

        # Set window icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.ico")
            self.root.iconbitmap(icon_path)
        except:
            pass

        # Setup Fullscreen
        self.root.attributes("-fullscreen", True)
        self.root.config(cursor="none") # Hide mouse cursor
        self.root.bind("<Control-Alt-l>", self.admin_unlock) # Admin Shortcut
        self.root.bind("<Escape>", self.admin_unlock) # Emergency Shortcut
        self.root.protocol("WM_DELETE_WINDOW", self.disable_event)

        # Fail-Safe State
        self.fail_count = 0
        self.offline_mode_triggered = False

        # UI Styling
        self.bg_color = "#0f172a" # Deep Blue/Black Slate
        self.accent_color = "#38bdf8" # Sky Blue
        self.text_color = "#ffffff"
        self.root.configure(bg=self.bg_color)

        self.setup_ui()

        # Matrix Digital Rain
        self.matrix_running = False
        self.root.after(200, self.init_matrix_rain)  # Tunggu window render dulu

        # Start Logic
        self.register_session()
        self.check_status_loop()
        self.update_clock()

    def load_config(self):
        # Cari config.json — prioriti: exe directory > current dir > Program Files
        search_paths = [
            os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)),
            os.getcwd(),
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "LabSentinel")
        ]
        config_path = None
        for path in search_paths:
            candidate = os.path.join(path, CONFIG_FILE)
            if os.path.exists(candidate):
                config_path = candidate
                break

        if not config_path:
            messagebox.showerror("Configuration Error", "Config file not found. Please run LabSentinel Setup first.")
            self.root.destroy()
            return {}
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Invalid config file: {e}")
            return {}

    def setup_ui(self):
        # Matrix Rain Canvas (Background layer - penuh skrin)
        self.matrix_canvas = tk.Canvas(self.root, bg=self.bg_color, highlightthickness=0)
        self.matrix_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # === HEADER (strip nipis di atas) ===
        self.header_frame = tk.Frame(self.root, bg=self.bg_color)
        self.header_frame.place(relx=0, rely=0, relwidth=1, height=80)

        header_inner = tk.Frame(self.header_frame, bg=self.bg_color)
        header_inner.pack(fill=tk.X, padx=50, pady=15)

        # Logo
        try:
            logo_img = Image.open("logo.png").resize((50, 50), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(header_inner, image=self.logo_photo, bg=self.bg_color).pack(side=tk.LEFT, padx=10)
        except:
            pass

        tk.Label(header_inner, text="LabSentinel", font=("Segoe UI", 24, "bold"), fg=self.text_color, bg=self.bg_color).pack(side=tk.LEFT)
        tk.Label(header_inner, text=f"| {self.lab_name}", font=("Segoe UI Light", 24), fg="#94a3b8", bg=self.bg_color).pack(side=tk.LEFT, padx=10)

        # Date/Time (Top Right)
        self.date_label = tk.Label(header_inner, text="", font=("Segoe UI", 12), fg="#94a3b8", bg=self.bg_color)
        self.date_label.pack(side=tk.RIGHT, padx=(0, 20))
        self.time_label = tk.Label(header_inner, text="", font=("Segoe UI", 18), fg=self.accent_color, bg=self.bg_color)
        self.time_label.pack(side=tk.RIGHT)

        # Countdown Timer
        self.countdown_label = tk.Label(header_inner, text="", font=("Segoe UI", 14, "bold"), fg="#22c55e", bg=self.bg_color)
        self.countdown_label.pack(side=tk.RIGHT, padx=(0, 30))

        # === LEFT PANEL (Teks arahan - compact, matrix rain nampak di sekeliling) ===
        self.left_panel = tk.Frame(self.root, bg=self.bg_color)
        self.left_panel.place(relx=0.05, rely=0.13)

        tk.Label(self.left_panel, text="Access Restricted", font=("Segoe UI", 36, "bold"), fg="white", bg=self.bg_color, anchor="w").pack(anchor="w")
        tk.Label(self.left_panel, text=f"This workstation ({self.pc_name}) is currently locked.", font=("Segoe UI", 18), fg="#94a3b8", bg=self.bg_color, anchor="w").pack(anchor="w", pady=10)

        instr_text = "1. Scan the QR code with your mobile device.\n2. Tap 'Unlock' on the web page.\n3. Wait for the system to verify access."
        tk.Label(self.left_panel, text=instr_text, font=("Segoe UI", 14), fg="#cbd5e1", bg=self.bg_color, justify=tk.LEFT, anchor="w").pack(anchor="w", pady=30)

        # === QR CODE (tiada frame besar - label sahaja) ===
        self.qr_label = tk.Label(self.root, bg="white", relief="solid", borderwidth=4)
        self.qr_label.place(relx=0.78, rely=0.18, anchor="n")

        # === STATUS LABEL (tengah bawah) ===
        self.status_label = tk.Label(self.root, text="● System Locked - Waiting for authorization...", font=("Consolas", 12), fg="#ef4444", bg=self.bg_color)
        self.status_label.place(relx=0.5, rely=0.78, anchor="center")

        # === OFFLINE BUTTON (hidden - akan dipaparkan oleh set_offline_mode) ===
        self.btn_offline = tk.Button(self.root, text="OFFLINE MODE - CLICK TO UNLOCK", command=self.admin_unlock,
                                   font=("Segoe UI", 14, "bold"), bg="#ef4444", fg="white", activebackground="#b91c1c",
                                   activeforeground="white", relief="raised", padx=20, pady=10)

        # === FOOTER (strip nipis di bawah) ===
        self.footer = tk.Frame(self.root, bg=self.bg_color)
        self.footer.place(relx=0, rely=1.0, relwidth=1, anchor="sw", height=50)

        tk.Label(self.footer, text="Powered by HelmiSoftTech", font=("Segoe UI", 10), fg="#64748b", bg=self.bg_color).pack(side=tk.RIGHT, padx=30)

        # Admin Unlock Button
        self.btn_admin = tk.Button(self.footer, text="Admin / Manual Unlock", command=self.admin_unlock,
                                   font=("Segoe UI", 9), bg="#1e293b", fg="white", activebackground="#334155",
                                   activeforeground="white", relief="flat", padx=10, pady=5)
        self.btn_admin.pack(side=tk.LEFT, padx=30)

    def init_matrix_rain(self):
        """Initialize Matrix Digital Rain columns"""
        self.matrix_chars = "ابتثجحخدذرزسشصضطظعغفقكلمنوهيءچڠڤڽۏئإأآةى0123456789"
        self.root.update_idletasks()
        w = self.root.winfo_width() or 1920
        h = self.root.winfo_height() or 1080

        col_spacing = 25
        num_cols = w // col_spacing
        self.matrix_columns = []
        for i in range(num_cols):
            x = i * col_spacing + col_spacing // 2
            y = random.randint(-h, 0)
            speed = random.randint(4, 14)
            length = random.randint(8, 22)
            self.matrix_columns.append({
                'x': x, 'y': y, 'speed': speed, 'length': length,
                'chars': [random.choice(self.matrix_chars) for _ in range(length)]
            })
        self.matrix_running = True
        self.animate_matrix()

    def animate_matrix(self):
        """Animate Matrix Digital Rain effect"""
        if not self.matrix_running:
            return

        self.matrix_canvas.delete("rain")
        h = self.root.winfo_height() or 1080

        for col in self.matrix_columns:
            for j in range(col['length']):
                cy = col['y'] + j * 20
                if cy < -20 or cy > h + 20:
                    continue
                char = col['chars'][j]
                # Kepala (head) = putih terang, badan = hijau, ekor = gelap
                if j == 0:
                    color = "#ffffff"
                    fnt = ("Consolas", 13, "bold")
                elif j < 3:
                    color = "#39ff14"
                    fnt = ("Consolas", 12)
                elif j < col['length'] // 2:
                    color = "#00cc33"
                    fnt = ("Consolas", 11)
                else:
                    color = "#004400"
                    fnt = ("Consolas", 10)
                self.matrix_canvas.create_text(
                    col['x'], cy, text=char, fill=color,
                    font=fnt, tags="rain"
                )

            # Gerakkan lajur ke bawah
            col['y'] += col['speed']

            # Rawak tukar aksara sekali-sekala
            if random.random() < 0.08:
                idx = random.randint(0, col['length'] - 1)
                col['chars'][idx] = random.choice(self.matrix_chars)

            # Reset bila keluar skrin
            if col['y'] - col['length'] * 20 > h:
                col['y'] = random.randint(-400, -30)
                col['speed'] = random.randint(4, 14)
                col['length'] = random.randint(8, 22)
                col['chars'] = [random.choice(self.matrix_chars) for _ in range(col['length'])]

        self.root.after(75, self.animate_matrix)

    def stop_matrix_rain(self):
        """Hentikan animasi matrix rain"""
        self.matrix_running = False
        if hasattr(self, 'matrix_canvas'):
            self.matrix_canvas.delete("rain")

    def disable_event(self):
        pass

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def get_mac_address(self):
        """Dapatkan MAC address adapter rangkaian aktif"""
        try:
            result = subprocess.run(
                ["getmac", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.strip().split('\n'):
                parts = line.replace('"', '').split(',')
                if len(parts) >= 2 and parts[0] and parts[0] != 'N/A':
                    return parts[0].strip()
        except:
            pass
        # Fallback menggunakan uuid
        try:
            import uuid as _uuid
            mac = _uuid.getnode()
            return ':'.join(f'{(mac >> i) & 0xFF:02X}' for i in range(40, -1, -8))
        except:
            return "00:00:00:00:00:00"

    def register_session(self):
        def thread():
            try:
                payload = {
                    "uuid": self.session_uuid,
                    "lab_name": self.lab_name,
                    "pc_name": self.pc_name,
                    "mac_address": self.get_mac_address()
                }
                response = requests.post(f"{self.server_url}/api.php?action=register", data=payload, timeout=5)
                
                if response.status_code != 200:
                    print(f"Registration Failed: {response.text}")
                    self.status_label.config(text=f"● CONNECTION ERROR: {response.status_code}", fg="#f59e0b")
            except Exception as e:
                print(f"Connection Error: {e}")
                self.status_label.config(text="● SERVER CONNECTION FAILED", fg="#ef4444")
        threading.Thread(target=thread, daemon=True).start()

    def set_offline_mode(self):
        if self.offline_mode_triggered: return
        self.offline_mode_triggered = True
        self.status_label.config(text="● SERVER UNREACHABLE - ENTERING OFFLINE MODE", fg="#f59e0b")
        self.btn_offline.place(relx=0.5, rely=0.85, anchor="center")

    def update_clock(self):
        if not self.is_unlocked:
            # Enforce Topmost and Fullscreen actively
            self.root.attributes("-topmost", True)
            self.root.lift()
            
            now = time.strftime("%H:%M:%S")
            date = time.strftime("%A, %d %B %Y")
            self.time_label.config(text=now)
            self.date_label.config(text=date)
            
            # QR Code Generation (Fix for Localhost)
            # If server_url has localhost, we must replace it for the QR code specifically
            qr_base_url = self.server_url
            if "localhost" in qr_base_url or "127.0.0.1" in qr_base_url:
                local_ip = self.get_local_ip()
                qr_base_url = qr_base_url.replace("localhost", local_ip).replace("127.0.0.1", local_ip)
            
            unlock_link = f"{qr_base_url}/unlock.php?uuid={self.session_uuid}"
            
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(unlock_link)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Resize for UI
            img = img.resize((250, 250), Image.Resampling.LANCZOS)
            self.qr_img = ImageTk.PhotoImage(img)
            self.qr_label.config(image=self.qr_img)
            
            # Schedule next update
            self.root.after(1000, self.update_clock)

    def check_status_loop(self):
        if self.is_unlocked: return

        def check_thread():
            try:
                res = requests.get(f"{self.api_url}?action=check&uuid={self.session_uuid}", timeout=3)
                if res.status_code == 200:
                    data = res.json()
                    if data.get('status') == 'UNLOCKED':
                        self.unlock_pc()
                    # Reset fail count on success
                    if self.fail_count > 0:
                        self.fail_count = 0 
            except Exception as e:
                self.fail_count += 1
                print(f"Connection failed: {e}")
                if self.fail_count >= 5: # Limit increased to 5
                     self.root.after(0, self.set_offline_mode)

        threading.Thread(target=check_thread, daemon=True).start()
        self.root.after(2000, self.check_status_loop)

    def open_admin_panel(self):
        """Buka Admin Panel di browser (perlu password)"""
        pwd = simpledialog.askstring("Admin Panel", "Masukkan Admin Password:", show="*", parent=self.root)
        if pwd == self.admin_password:
            import webbrowser
            webbrowser.open(f"{self.server_url}/admin")
        elif pwd is not None:
            messagebox.showerror("Error", "Password salah.")

    def open_settings(self):
        """Buka config.json untuk edit settings (perlu password)"""
        pwd = simpledialog.askstring("Settings", "Masukkan Admin Password:", show="*", parent=self.root)
        if pwd == self.admin_password:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)
            os.startfile(config_path)
        elif pwd is not None:
            messagebox.showerror("Error", "Password salah.")

    def admin_unlock(self, event=None):
        pwd = simpledialog.askstring("Admin Unlock", "Enter Admin Password:", show="*", parent=self.root)
        if pwd == self.admin_password:
            self.unlock_pc(admin=True)
        elif pwd is not None:
            messagebox.showerror("Error", "Incorrect Password")

    def unlock_pc(self, admin=False):
        self.is_unlocked = True
        self.stop_matrix_rain()
        self.root.config(cursor="arrow")
        self.root.attributes("-fullscreen", False)
        self.root.attributes("-topmost", False)

        # Sorok semua elemen kecuali countdown dan status
        self.left_panel.place_forget()
        self.qr_label.place_forget()
        self.footer.place_forget()
        self.header_frame.place_forget()
        self.matrix_canvas.place_forget()

        # Papar hanya status dan countdown di tengah
        self.status_label.config(text="● ACCESS GRANTED\nSesi Bermula", fg="#22c55e", font=("Segoe UI", 11, "bold"))
        self.status_label.place(relx=0.5, rely=0.28, anchor="center")

        # Buat label countdown baru (anak root) supaya tak hilang dengan header
        self.unlock_countdown = tk.Label(self.root, text="", font=("Consolas", 36, "bold"), fg="#22c55e", bg=self.bg_color)
        self.unlock_countdown.place(relx=0.5, rely=0.55, anchor="center")

        # Butang Admin Panel & Settings
        self.unlock_btn_frame = tk.Frame(self.root, bg=self.bg_color)
        self.unlock_btn_frame.place(relx=0.5, rely=0.88, anchor="center")

        tk.Button(self.unlock_btn_frame, text="Admin Panel", command=self.open_admin_panel,
                  font=("Segoe UI", 9), bg="#1e293b", fg="white", activebackground="#334155",
                  activeforeground="white", relief="flat", padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=5)

        tk.Button(self.unlock_btn_frame, text="Settings", command=self.open_settings,
                  font=("Segoe UI", 9), bg="#1e293b", fg="white", activebackground="#334155",
                  activeforeground="white", relief="flat", padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Set saiz window kecil
        self.root.geometry("420x280")
        self.root.resizable(False, False)

        if admin:
            messagebox.showinfo("Admin", "Unlocked via Admin Override")

        # Mulakan countdown
        self.remaining_time = SESSION_TIME_LIMIT
        self.start_countdown()

        # Minimize window
        self.root.iconify()

    def start_countdown(self):
        """Mulakan countdown timer untuk sesi pengguna"""
        self.update_countdown()

    def update_countdown(self):
        """Kemas kini countdown setiap saat"""
        if self.remaining_time > 0:
            hours = self.remaining_time // 3600
            minutes = (self.remaining_time % 3600) // 60
            seconds = self.remaining_time % 60

            time_str = f"⏱ {hours:02d}:{minutes:02d}:{seconds:02d}"

            # Tukar warna berdasarkan masa berbaki
            if self.remaining_time <= 300:  # 5 minit terakhir - merah
                color = "#ef4444"
            elif self.remaining_time <= 900:  # 15 minit terakhir - oren
                color = "#f59e0b"
            else:  # Masa masih banyak - hijau
                color = "#22c55e"

            self.countdown_label.config(text=time_str, fg=color)
            if hasattr(self, 'unlock_countdown'):
                self.unlock_countdown.config(text=time_str, fg=color)

            self.remaining_time -= 1
            self.root.after(1000, self.update_countdown)
        else:
            # Masa tamat - kunci semula PC
            self.lock_pc()

    def lock_pc(self):
        """Kunci PC apabila masa tamat"""
        self.is_unlocked = False
        self.remaining_time = SESSION_TIME_LIMIT
        self.session_uuid = str(uuid.uuid4())  # Jana UUID baru

        # Buang elemen unlock view
        if hasattr(self, 'unlock_countdown'):
            self.unlock_countdown.destroy()
            del self.unlock_countdown
        if hasattr(self, 'unlock_btn_frame'):
            self.unlock_btn_frame.destroy()
            del self.unlock_btn_frame

        # Reset UI - pulihkan semua elemen
        self.root.deiconify()
        self.root.resizable(True, True)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.config(cursor="none")

        # Pulihkan elemen yang disorok
        self.matrix_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.header_frame.place(relx=0, rely=0, relwidth=1, height=80)
        self.left_panel.place(relx=0.05, rely=0.13)
        self.qr_label.place(relx=0.78, rely=0.18, anchor="n")
        self.footer.place(relx=0, rely=1.0, relwidth=1, anchor="sw", height=50)

        # Reset offline state
        self.offline_mode_triggered = False
        self.fail_count = 0
        self.btn_offline.place_forget()

        # Reset label ke saiz asal
        self.status_label.config(text="● SESI TAMAT - Sila Imbas QR Semula", fg="#ef4444", font=("Consolas", 12))
        self.status_label.place(relx=0.5, rely=0.78, anchor="center")
        self.countdown_label.config(text="", font=("Segoe UI", 14, "bold"))

        # Mulakan semula matrix rain
        self.init_matrix_rain()

        # Daftar sesi baru
        self.register_session()
        self.check_status_loop()
        self.update_clock()

if __name__ == "__main__":
    root = tk.Tk()
    app = LockScreenApp(root)
    root.mainloop()
