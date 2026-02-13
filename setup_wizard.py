import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import shutil
import ctypes
import winreg
import subprocess
import threading
import urllib.request
from PIL import Image, ImageTk # pip install pillow

# Set AppUserModelID supaya Windows guna ikon app, bukan ikon Python
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HelmiSoftTech.LabSentinel.Setup.1")
except:
    pass

# --- CONFIGURATION DEFAULTS ---
DEFAULT_SERVER_URL = "https://labsentinel.xyz"
CONFIG_FILE = "config.json"
INSTALL_DIR = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "LabSentinel")
APP_VERSION = "1.0.0"


class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("LabSentinel - Setup Wizard")
        self.geometry("700x500")
        self.resizable(False, False)

        # Tentukan source directory (di mana Setup EXE dijalankan)
        if getattr(sys, 'frozen', False):
            self.source_dir = os.path.dirname(sys.executable)
        else:
            self.source_dir = os.path.dirname(os.path.abspath(__file__))

        # Load Images explicitly first to use for Icon
        self.load_images()

        # Set Window Icon (Top-Left) - guna .ico untuk Windows
        try:
            search_paths = [
                os.path.dirname(os.path.abspath(__file__)),
                os.getcwd()
            ]
            if getattr(sys, 'frozen', False):
                search_paths.append(os.path.dirname(sys.executable))
            for path in search_paths:
                ico_path = os.path.join(path, "logo.ico")
                if os.path.exists(ico_path):
                    self.iconbitmap(ico_path)
                    break
            else:
                # Fallback ke PNG jika ICO tiada
                if self.logo_photo:
                    self.iconphoto(False, self.logo_photo)
        except:
            if self.logo_photo:
                self.iconphoto(False, self.logo_photo)

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="white")
        self.style.configure("TLabel", background="white", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground="#1a3a6e")

        self.configure(bg="white")

        # Data Store
        self.config_data = {
            "lab_name": tk.StringVar(),
            "pc_name": tk.StringVar(),
            "admin_password": tk.StringVar(),
            "server_url": tk.StringVar(value=DEFAULT_SERVER_URL)
        }

        # Wizard Steps
        self.steps = [
            self.create_welcome_step,
            self.create_details_step,
            self.create_security_step,
            self.create_finish_step
        ]
        self.current_step = 0

        # UI Layout
        # Sidebar (Pack First to take full left height)
        self.create_sidebar()

        # Navigation Buttons Frame (Pack Second to take bottom of remaining right area)
        self.nav_frame = tk.Frame(self, bg="#f0f0f0", height=50)
        self.nav_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.nav_frame.pack_propagate(False)

        self.btn_next = ttk.Button(self.nav_frame, text="Next >", command=self.next_step)
        self.btn_next.pack(side=tk.RIGHT, padx=20, pady=10)

        self.btn_back = ttk.Button(self.nav_frame, text="< Back", command=self.prev_step)
        self.btn_back.pack(side=tk.RIGHT, padx=10, pady=10)
        self.btn_back.state(["disabled"])

        self.lbl_branding = tk.Label(self.nav_frame, text="HelmiSoftTech © 2026", bg="#f0f0f0", fg="gray", font=("Arial", 8))
        self.lbl_branding.pack(side=tk.LEFT, padx=20)

        # Main Content (Takes remaining space)
        self.main_area = ttk.Frame(self, style="TFrame")
        self.main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Start
        self.show_step(0)

    def load_images(self):
        try:
            # Search paths for assets
            search_paths = [
                os.path.dirname(os.path.abspath(__file__)), # Script/Frozen Temp Dir
                os.getcwd() # Current Working Directory
            ]

            # If frozen (exe), add the executable's directory
            if getattr(sys, 'frozen', False):
                search_paths.append(os.path.dirname(sys.executable))

            # Helper to find file
            def find_asset(filename):
                for path in search_paths:
                    full_path = os.path.join(path, filename)
                    if os.path.exists(full_path):
                        return full_path
                return None

            banner_path = find_asset("banner.png")
            logo_path = find_asset("logo.png")

            # Pillow compatibility
            resample_method = Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS
            if hasattr(Image, "Resampling"):
                resample_method = Image.Resampling.LANCZOS

            # Banner - Resize to fill sidebar (200x500 matches window height)
            if banner_path:
                banner_img = Image.open(banner_path).resize((200, 500), resample_method)
                self.banner_photo = ImageTk.PhotoImage(banner_img)
            else:
                self.banner_photo = None

            # Logo
            if logo_path:
                logo_img = Image.open(logo_path).resize((60, 60), resample_method)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
            else:
                 self.logo_photo = None

        except Exception as e:
            messagebox.showerror("Image Load Error", f"Failed to load images: {e}")
            self.banner_photo = None
            self.logo_photo = None

    def create_sidebar(self):
        # Left sidebar with banner
        if self.banner_photo:
            sidebar = tk.Label(self, image=self.banner_photo, bg="#1a3a6e", bd=0)
        else:
            # Fallback if image missing
            sidebar = tk.Label(self, text="BANNER\nMISSING", fg="white", bg="#1a3a6e", width=25)

        sidebar.pack(side=tk.LEFT, fill=tk.Y)

    def clear_main_area(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

    def show_step(self, index):
        self.clear_main_area()
        self.steps[index]()

        # specific button logic
        if index == 0:
            self.btn_back.state(["disabled"])
            self.btn_next.config(text="Next >", command=self.next_step)
        elif index == len(self.steps) - 1: # Finish step
            self.btn_back.pack_forget()
            self.btn_next.config(text="Install", command=self.finish_setup)
        else:
            self.btn_back.state(["!disabled"])
            self.btn_next.config(text="Next >", command=self.next_step)

    def next_step(self):
        if not self.validate_step(self.current_step):
            return

        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.show_step(self.current_step)

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step(self.current_step)

    def validate_step(self, step_index):
        if step_index == 1: # Details
            if not self.config_data["lab_name"].get():
                messagebox.showwarning("Input Diperlukan", "Sila pilih Makmal.")
                return False
            if not self.config_data["pc_name"].get():
                messagebox.showwarning("Input Diperlukan", "Sila pilih Nombor PC.")
                return False
        if step_index == 2: # Security
            if not self.config_data["admin_password"].get():
                messagebox.showwarning("Input Diperlukan", "Sila masukkan Admin Password untuk emergency unlock.")
                return False
        return True

    # --- STEPS ---

    # --- PYTHON INSTALLER ---
    PYTHON_VERSION = "3.12.9"
    PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-amd64.exe"
    PYTHON_FILENAME = f"python-{PYTHON_VERSION}-amd64.exe"

    def check_python(self):
        """Semak sama ada Python dipasang pada sistem"""
        for cmd in ["python", "py"]:
            try:
                proc = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                output = (proc.stdout + proc.stderr).strip()
                if "Python" in output and "not found" not in output.lower():
                    return {'found': True, 'version': output}
            except Exception:
                pass
        return {'found': False, 'version': ''}

    def check_libraries(self):
        """Semak library Python yang diperlukan"""
        libs = {'requests': False, 'qrcode': False, 'pillow (PIL)': False}
        for lib, import_name in [('requests', 'requests'), ('qrcode', 'qrcode'), ('pillow (PIL)', 'PIL')]:
            try:
                proc = subprocess.run(
                    ["python", "-c", f"import {import_name}; print('OK')"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if "OK" in proc.stdout:
                    libs[lib] = True
            except Exception:
                pass
        return libs

    def download_and_install_python(self):
        """Muat turun dan pasang Python secara automatik"""
        self.btn_download_py.config(state="disabled", text="Memuat turun...")
        self.py_progress_label.config(text="Menyambung ke python.org...")

        def download_thread():
            download_path = os.path.join(os.environ.get("TEMP", "."), self.PYTHON_FILENAME)
            try:
                # Muat turun dengan progress
                req = urllib.request.urlopen(self.PYTHON_URL, timeout=30)
                total_size = int(req.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 65536

                with open(download_path, 'wb') as f:
                    while True:
                        chunk = req.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int(downloaded / total_size * 100)
                            mb_done = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            self.root.after(0, lambda p=pct, d=mb_done, t=mb_total:
                                self.py_progress_label.config(
                                    text=f"Memuat turun: {p}% ({d:.1f}/{t:.1f} MB)"))

                self.root.after(0, lambda: self.py_progress_label.config(
                    text="Memasang Python (sila tunggu)..."))

                # Pasang Python secara senyap dengan PATH
                proc = subprocess.run(
                    [download_path, "/passive", "InstallAllUsers=1",
                     "PrependPath=1", "Include_test=0"],
                    timeout=300
                )

                # Bersih
                try:
                    os.remove(download_path)
                except Exception:
                    pass

                if proc.returncode == 0:
                    # Pasang library
                    self.root.after(0, lambda: self.py_progress_label.config(
                        text="Memasang library (requests, qrcode, pillow)..."))
                    subprocess.run(
                        ["python", "-m", "pip", "install", "requests", "qrcode", "pillow"],
                        capture_output=True, timeout=120,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    self.root.after(0, self.on_python_install_success)
                else:
                    self.root.after(0, lambda: self.on_python_install_fail(
                        f"Installer keluar dengan kod {proc.returncode}"))

            except Exception as e:
                try:
                    os.remove(download_path)
                except Exception:
                    pass
                self.root.after(0, lambda: self.on_python_install_fail(str(e)))

        threading.Thread(target=download_thread, daemon=True).start()

    def on_python_install_success(self):
        """Dipanggil selepas Python berjaya dipasang"""
        self.py_progress_label.config(text="")
        self.btn_download_py.pack_forget()
        # Refresh welcome step
        self.show_step(0)
        messagebox.showinfo("Berjaya",
            f"Python {self.PYTHON_VERSION} dan library berjaya dipasang!\n\n"
            "Semua keperluan sistem telah dipenuhi.")

    def on_python_install_fail(self, error):
        """Dipanggil jika pemasangan Python gagal"""
        self.py_progress_label.config(text=f"Gagal: {error}", fg="#dc2626")
        self.btn_download_py.config(state="normal", text="Cuba Semula")

    def create_welcome_step(self):
        header = ttk.Label(self.main_area, text="Welcome to LabSentinel Setup", style="Header.TLabel")
        header.pack(anchor="w", pady=(10, 5))

        desc = ttk.Label(self.main_area, text="This wizard will install LabSentinel and configure\nit for this workstation.", wraplength=400)
        desc.pack(anchor="w", pady=(0, 10))

        # --- System Requirements Check ---
        req_frame = tk.LabelFrame(self.main_area, text="  System Requirements  ", font=("Segoe UI", 10, "bold"),
                                   bg="white", fg="#1a3a6e", padx=15, pady=10)
        req_frame.pack(fill=tk.X, pady=(0, 10))

        # Semak Python
        py_info = self.check_python()

        if py_info['found']:
            py_icon, py_color = "OK", "#16a34a"
            py_text = f"Python — {py_info['version']}"
        else:
            py_icon, py_color = "X", "#dc2626"
            py_text = "Python — Tidak dijumpai"

        py_row = tk.Frame(req_frame, bg="white")
        py_row.pack(fill=tk.X, pady=2)
        tk.Label(py_row, text=f"[{py_icon}]", font=("Consolas", 10, "bold"), fg=py_color, bg="white", width=4, anchor="w").pack(side=tk.LEFT)
        tk.Label(py_row, text=py_text, font=("Segoe UI", 10), bg="white", fg="#333").pack(side=tk.LEFT)

        # Semak library (hanya jika Python ada)
        libs = {}
        if py_info['found']:
            libs = self.check_libraries()
            for lib_name, installed in libs.items():
                lib_row = tk.Frame(req_frame, bg="white")
                lib_row.pack(fill=tk.X, pady=1)
                icon = "OK" if installed else "X"
                color = "#16a34a" if installed else "#dc2626"
                tk.Label(lib_row, text=f"[{icon}]", font=("Consolas", 10, "bold"), fg=color, bg="white", width=4, anchor="w").pack(side=tk.LEFT)
                status_text = lib_name if installed else f"{lib_name} — Tidak dipasang"
                tk.Label(lib_row, text=f"  {status_text}", font=("Segoe UI", 9), bg="white", fg="#555").pack(side=tk.LEFT)

        all_libs_ok = all(libs.values()) if py_info['found'] else False

        if not py_info['found']:
            # Python tidak dijumpai — tawar muat turun
            warn_frame = tk.Frame(req_frame, bg="#fef2f2", highlightbackground="#fecaca", highlightthickness=1)
            warn_frame.pack(fill=tk.X, pady=(10, 0))
            tk.Label(warn_frame, text="Python diperlukan untuk menjalankan LabSentinel Client.",
                     font=("Segoe UI", 9), bg="#fef2f2", fg="#991b1b", padx=10, pady=(8, 4)).pack(anchor="w")

            btn_frame = tk.Frame(warn_frame, bg="#fef2f2")
            btn_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

            self.btn_download_py = tk.Button(btn_frame,
                text=f"Muat Turun && Pasang Python {self.PYTHON_VERSION}",
                command=self.download_and_install_python,
                font=("Segoe UI", 10, "bold"), bg="#1a3a6e", fg="white",
                activebackground="#2d5a9e", activeforeground="white",
                relief="raised", padx=15, pady=6, cursor="hand2")
            self.btn_download_py.pack(anchor="w", pady=(4, 4))

            self.py_progress_label = tk.Label(btn_frame, text="", font=("Segoe UI", 8),
                                               bg="#fef2f2", fg="#555", anchor="w")
            self.py_progress_label.pack(anchor="w")

        elif not all_libs_ok:
            # Python ada tapi library tak cukup — install automatik
            missing = [lib for lib, ok in libs.items() if not ok]
            warn_frame = tk.Frame(req_frame, bg="#fffbeb", highlightbackground="#fef08a", highlightthickness=1)
            warn_frame.pack(fill=tk.X, pady=(10, 0))
            pip_libs = " ".join([("pillow" if "pillow" in m else m) for m in missing])
            tk.Label(warn_frame, text=f"Library belum dipasang: {', '.join(missing)}",
                     font=("Segoe UI", 9), bg="#fffbeb", fg="#92400e", padx=10, pady=(8, 4)).pack(anchor="w")

            lib_btn_frame = tk.Frame(warn_frame, bg="#fffbeb")
            lib_btn_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

            self.py_progress_label = tk.Label(lib_btn_frame, text="", font=("Segoe UI", 8),
                                               bg="#fffbeb", fg="#555", anchor="w")

            def install_libs():
                btn_install_libs.config(state="disabled", text="Memasang...")
                def thread():
                    try:
                        subprocess.run(
                            ["python", "-m", "pip", "install", pip_libs],
                            capture_output=True, timeout=120,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        self.root.after(0, lambda: [self.show_step(0),
                            messagebox.showinfo("Berjaya", "Library berjaya dipasang!")])
                    except Exception as e:
                        self.root.after(0, lambda: [
                            self.py_progress_label.config(text=f"Gagal: {e}", fg="#dc2626"),
                            btn_install_libs.config(state="normal", text="Cuba Semula")])
                threading.Thread(target=thread, daemon=True).start()

            btn_install_libs = tk.Button(lib_btn_frame,
                text=f"Pasang Library ({pip_libs})",
                command=install_libs,
                font=("Segoe UI", 9, "bold"), bg="#92400e", fg="white",
                activebackground="#78350f", activeforeground="white",
                relief="raised", padx=10, pady=4, cursor="hand2")
            btn_install_libs.pack(anchor="w", pady=(4, 4))
            self.py_progress_label.pack(anchor="w")

        else:
            # Semua OK
            ok_frame = tk.Frame(req_frame, bg="#f0fdf4", highlightbackground="#bbf7d0", highlightthickness=1)
            ok_frame.pack(fill=tk.X, pady=(10, 0))
            tk.Label(ok_frame, text="Semua keperluan sistem dipenuhi.", font=("Segoe UI", 9, "bold"),
                     bg="#f0fdf4", fg="#16a34a", padx=10, pady=6).pack(anchor="w")

        install_info = f"Lokasi pemasangan: {INSTALL_DIR}"
        ttk.Label(self.main_area, text=install_info, font=("Consolas", 9), foreground="#1a3a6e").pack(anchor="w", pady=(10, 0))

        ttk.Label(self.main_area, text="Click Next to continue.").pack(anchor="w", pady=(5, 0))

    def create_details_step(self):
        header = ttk.Label(self.main_area, text="Maklumat Workstation", style="Header.TLabel")
        header.pack(anchor="w", pady=(10, 20))

        frame = ttk.Frame(self.main_area, style="TFrame")
        frame.pack(fill=tk.X, pady=10)

        ttk.Label(frame, text="Nama Makmal:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.config_data["lab_name"], width=40).grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(frame, text="Contoh: Makmal Cyber Security", font=("Arial", 8), foreground="gray").grid(row=2, column=0, sticky="w")

        ttk.Label(frame, text="Nama PC:").grid(row=3, column=0, sticky="w", pady=(15, 5))
        ttk.Entry(frame, textvariable=self.config_data["pc_name"], width=40).grid(row=4, column=0, sticky="w", pady=5)
        ttk.Label(frame, text="Contoh: PC CS00, PC CS01, PC MM05", font=("Arial", 8), foreground="gray").grid(row=5, column=0, sticky="w")

    def create_security_step(self):
        header = ttk.Label(self.main_area, text="Security & Connection", style="Header.TLabel")
        header.pack(anchor="w", pady=(10, 20))

        frame = ttk.Frame(self.main_area, style="TFrame")
        frame.pack(fill=tk.X, pady=10)

        ttk.Label(frame, text="Admin Password (untuk manual unlock):").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.config_data["admin_password"], show="*", width=40).grid(row=1, column=0, sticky="w", pady=5)

        ttk.Label(frame, text="Server URL:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.config_data["server_url"], width=40).grid(row=3, column=0, sticky="w", pady=5)

        help_text = "URL sudah ditetapkan: https://labsentinel.xyz\nTukar hanya jika diarahkan oleh pentadbir."
        ttk.Label(frame, text=help_text, font=("Arial", 8), foreground="gray", justify=tk.LEFT).grid(row=4, column=0, sticky="w")

        # Startup Option
        self.config_data["auto_start"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Start LabSentinel automatik bila PC dihidupkan?", variable=self.config_data["auto_start"]).grid(row=5, column=0, sticky="w", pady=(10, 0))

    def create_finish_step(self):
        header = ttk.Label(self.main_area, text="Ready to Install", style="Header.TLabel")
        header.pack(anchor="w", pady=(10, 20))

        summary = f"""
        Summary of Configuration:
        -------------------------
        Lab Name:    {self.config_data['lab_name'].get()}
        PC Name:     {self.config_data['pc_name'].get()}
        Server:      {self.config_data['server_url'].get()}
        Auto-Start:  {'Yes' if self.config_data['auto_start'].get() else 'No'}
        Install To:  {INSTALL_DIR}

        Click 'Install' to install and configure LabSentinel.
        """
        ttk.Label(self.main_area, text=summary, font=("Consolas", 10), background="#f9f9f9", relief="solid", borderwidth=1).pack(fill=tk.BOTH, expand=True, padx=0, pady=10)

    def install_files(self):
        """Copy fail-fail yang diperlukan ke C:\\Program Files\\LabSentinel"""
        os.makedirs(INSTALL_DIR, exist_ok=True)

        # Senarai fail yang perlu dicopy (termasuk Setup EXE untuk uninstall)
        files_to_copy = ["LabSentinel Client.exe", "LabSentinel Setup.exe", "logo.ico", "logo.png"]

        for filename in files_to_copy:
            src = os.path.join(self.source_dir, filename)
            dst = os.path.join(INSTALL_DIR, filename)
            if os.path.exists(src):
                shutil.copy2(src, dst)

    def save_config(self):
        """Simpan config.json ke install directory"""
        data = {
            "lab_name": self.config_data["lab_name"].get(),
            "pc_name": self.config_data["pc_name"].get(),
            "admin_password": self.config_data["admin_password"].get(),
            "server_url": self.config_data["server_url"].get(),
            "auto_start": self.config_data["auto_start"].get()
        }
        config_path = os.path.join(INSTALL_DIR, CONFIG_FILE)
        with open(config_path, "w") as f:
            json.dump(data, f, indent=4)

    def register_uninstall(self):
        """Daftar dalam Windows Installed Apps (Add/Remove Programs)"""
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\LabSentinel"
        client_exe = os.path.join(INSTALL_DIR, "LabSentinel Client.exe")
        icon_path = os.path.join(INSTALL_DIR, "logo.ico")

        # Uninstall command — panggil Setup EXE dalam mod uninstall (password protected)
        setup_exe = os.path.join(INSTALL_DIR, "LabSentinel Setup.exe")
        uninstall_cmd = f'"{setup_exe}" --uninstall'

        try:
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "LabSentinel")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "HelmiSoftTech")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, INSTALL_DIR)
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, icon_path)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_cmd)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

            # Kira saiz folder (dalam KB)
            total_size = 0
            for f in os.listdir(INSTALL_DIR):
                fp = os.path.join(INSTALL_DIR, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, total_size // 1024)

            winreg.CloseKey(key)
        except PermissionError:
            # Jika tiada admin rights, skip registry — fail masih tercopy
            pass

    def create_startup_shortcut(self):
        """Buat shortcut dalam Windows Startup folder"""
        startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        target_path = os.path.join(INSTALL_DIR, "LabSentinel Client.exe")
        shortcut_path = os.path.join(startup_folder, "LabSentinel.lnk")
        icon_path = os.path.join(INSTALL_DIR, "logo.ico")

        vbs_script = f"""
        Set oWS = WScript.CreateObject("WScript.Shell")
        sLinkFile = "{shortcut_path}"
        Set oLink = oWS.CreateShortcut(sLinkFile)
        oLink.TargetPath = "{target_path}"
        oLink.WorkingDirectory = "{INSTALL_DIR}"
        oLink.Description = "LabSentinel Lock Screen"
        oLink.IconLocation = "{icon_path}"
        oLink.Save
        """

        vbs_file = os.path.join(os.environ.get("TEMP", "."), "create_shortcut.vbs")
        with open(vbs_file, "w") as f:
            f.write(vbs_script)

        subprocess.run(["cscript", "//nologo", vbs_file], creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            os.remove(vbs_file)
        except:
            pass

    def remove_startup_shortcut(self):
        """Buang shortcut startup jika wujud"""
        shortcut_path = os.path.join(
            os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup', "LabSentinel.lnk"
        )
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)

    def finish_setup(self):
        """Proses pemasangan penuh"""
        try:
            # 1. Copy fail ke Program Files
            self.install_files()

            # 2. Simpan config.json
            self.save_config()

            # 3. Daftar dalam Installed Apps
            self.register_uninstall()

            # 4. Handle Auto-Start
            if self.config_data["auto_start"].get():
                try:
                    self.create_startup_shortcut()
                except Exception as e:
                    messagebox.showerror("Startup Error", f"Could not create startup shortcut: {e}")
            else:
                self.remove_startup_shortcut()

            messagebox.showinfo("Success",
                f"LabSentinel berjaya dipasang!\n\n"
                f"Lokasi: {INSTALL_DIR}\n\n"
                f"Anda boleh jalankan LabSentinel Client dari lokasi tersebut.")
            self.destroy()

        except PermissionError:
            messagebox.showerror("Error",
                "Gagal menulis ke Program Files.\n\n"
                "Sila jalankan Setup sebagai Administrator\n"
                "(Right-click → Run as administrator)")
        except Exception as e:
            messagebox.showerror("Error", f"Pemasangan gagal: {e}")


def run_uninstall():
    """Mod uninstall — memerlukan admin password sebelum padam"""
    import tkinter as tk
    from tkinter import simpledialog, messagebox

    root = tk.Tk()

    # Set icon SEBELUM withdraw supaya child windows inherit
    try:
        ico_path = os.path.join(INSTALL_DIR, "logo.ico")
        if os.path.exists(ico_path):
            root.iconbitmap(default=ico_path)
    except:
        pass

    root.withdraw()

    # Baca password dari config.json
    config_path = os.path.join(INSTALL_DIR, CONFIG_FILE)
    admin_password = None
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                admin_password = config.get("admin_password", "")
        except:
            pass

    if not admin_password:
        messagebox.showerror("Error", "Config file tidak ditemui. Uninstall dibatalkan.")
        root.destroy()
        return

    # Minta password
    pwd = simpledialog.askstring("LabSentinel Uninstall",
        "Masukkan Admin Password untuk uninstall:", show="*", parent=root)

    if pwd is None:
        root.destroy()
        return

    if pwd != admin_password:
        messagebox.showerror("Error", "Password salah. Uninstall dibatalkan.")
        root.destroy()
        return

    # Sahkan uninstall
    confirm = messagebox.askyesno("Sahkan Uninstall",
        f"Adakah anda pasti mahu uninstall LabSentinel?\n\n"
        f"Folder berikut akan dipadam:\n{INSTALL_DIR}\n\n"
        f"Startup shortcut juga akan dibuang.")

    if not confirm:
        root.destroy()
        return

    try:
        # 0. Bunuh LabSentinel Client jika sedang berjalan
        subprocess.run(
            ["taskkill", "/F", "/IM", "LabSentinel Client.exe"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True
        )

        # 1. Buang startup shortcut
        shortcut_path = os.path.join(
            os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup', "LabSentinel.lnk"
        )
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)

        # 2. Buang registry entry
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\LabSentinel"
        try:
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
        except:
            pass

        # 3. Padam folder install (delay supaya EXE sendiri boleh tutup dulu)
        #    Guna cmd /c dengan ping delay untuk bagi masa EXE exit
        bat_content = f"""@echo off
ping 127.0.0.1 -n 3 > nul
rmdir /s /q "{INSTALL_DIR}"
del "%~f0"
"""
        bat_path = os.path.join(os.environ.get("TEMP", "."), "labsentinel_uninstall.bat")
        with open(bat_path, "w") as f:
            f.write(bat_content)

        messagebox.showinfo("Berjaya", "LabSentinel telah dibuang.\n\nFolder akan dipadam sebentar lagi.")
        root.destroy()

        # Jalankan bat file untuk padam folder selepas EXE tutup
        subprocess.Popen(
            ["cmd", "/c", bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    except Exception as e:
        messagebox.showerror("Error", f"Uninstall gagal: {e}")
        root.destroy()


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        run_uninstall()
    else:
        app = SetupWizard()
        app.mainloop()
