import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import shutil
import ctypes
import winreg
import subprocess
from PIL import Image, ImageTk # pip install pillow

# Set AppUserModelID supaya Windows guna ikon app, bukan ikon Python
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HelmiSoftTech.LabSentinel.Setup.1")
except:
    pass

# --- CONFIGURATION DEFAULTS ---
DEFAULT_SERVER_URL = "https://linuxpredator.pythonanywhere.com"
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

    def create_welcome_step(self):
        header = ttk.Label(self.main_area, text="Welcome to LabSentinel Setup", style="Header.TLabel")
        header.pack(anchor="w", pady=(10, 20))

        desc = ttk.Label(self.main_area, text="This wizard will install LabSentinel and configure\nit for this workstation.\n\nPlease ensure you have your Lab Name and PC ID ready.", wraplength=400)
        desc.pack(anchor="w", pady=10)

        install_info = f"Lokasi pemasangan: {INSTALL_DIR}"
        ttk.Label(self.main_area, text=install_info, font=("Consolas", 9), foreground="#1a3a6e").pack(anchor="w", pady=5)

        ttk.Label(self.main_area, text="Click Next to continue.").pack(anchor="w", pady=20)

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

        help_text = "URL sudah ditetapkan: https://linuxpredator.pythonanywhere.com\nTukar hanya jika diarahkan oleh pentadbir."
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
