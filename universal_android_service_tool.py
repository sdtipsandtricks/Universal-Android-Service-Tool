"""
Universal Android Service Tool
Read-only ADB/FASTBOOT diagnostics + exact-match temporary-root profile manager.
No bootloader unlock, FRP operations, partition writes, exploit execution, or flashing.
"""
import os, sys, json, shutil, subprocess, threading, webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

APP_TITLE = "Universal Android Service Tool"
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
PROFILE_FILE = os.path.join(HERE, "profiles.json")

PROPS = [
    ("Manufacturer", "ro.product.manufacturer"),
    ("Brand", "ro.product.brand"),
    ("Model", "ro.product.model"),
    ("Device codename", "ro.product.device"),
    ("Product", "ro.build.product"),
    ("Android version", "ro.build.version.release"),
    ("SDK level", "ro.build.version.sdk"),
    ("Build ID", "ro.build.display.id"),
    ("Incremental build", "ro.build.version.incremental"),
    ("Build fingerprint", "ro.build.fingerprint"),
    ("Security patch", "ro.build.version.security_patch"),
    ("Bootloader locked (1=yes)", "ro.boot.flash.locked"),
    ("Verified Boot state", "ro.boot.verifiedbootstate"),
    ("Boot state", "ro.boot.bootstate"),
    ("CPU ABI", "ro.product.cpu.abi"),
    ("Hardware", "ro.hardware"),
]

def run(args, timeout=20):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

def safe_text(value):
    return value if value else "(not reported)"

class UniversalTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(1000, 650)
        self.adb = shutil.which("adb")
        self.fastboot = shutil.which("fastboot")
        self.serial = None
        self.info = {}
        self.profile = None
        self.profiles = self.load_profiles()
        self.brand_var = tk.StringVar(value="Auto detect")
        self.mode_var = tk.StringVar(value="ADB")
        self.operation_var = tk.StringVar(value="Read device information")
        self._style()
        self._ui()
        self.log("Universal Android Service Tool started.")
        self.refresh_tools()
        self.detect_adb(silent=True)

    def load_profiles(self):
        if not os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump({"schema_version":1,"profiles":[]}, f, indent=2)
        try:
            with open(PROFILE_FILE, encoding="utf-8") as f:
                data=json.load(f)
            return data if isinstance(data,dict) else {"profiles":[]}
        except Exception:
            return {"profiles":[]}

    def _style(self):
        self.configure(bg="#202328")
        st=ttk.Style(self)
        try: st.theme_use("clam")
        except tk.TclError: pass
        st.configure("TFrame",background="#292d33")
        st.configure("TLabel",background="#292d33",foreground="#e7eaf0",font=("Segoe UI",9))
        st.configure("TButton",font=("Segoe UI",9),padding=6)
        st.configure("TLabelframe",background="#292d33",foreground="#f4f5f7")
        st.configure("TLabelframe.Label",background="#292d33",foreground="#ffffff",font=("Segoe UI",9,"bold"))
        st.configure("TRadiobutton",background="#292d33",foreground="#e7eaf0")
        st.configure("TCombobox",fieldbackground="#171a1e",background="#3d424a",foreground="#ffffff")

    def _ui(self):
        header=ttk.Frame(self,padding=(12,10)); header.pack(fill="x")
        ttk.Label(header,text="Brand:").pack(side="left")
        brand=ttk.Combobox(header,textvariable=self.brand_var,state="readonly",width=18,
                           values=["Auto detect","OPPO","vivo","OnePlus","Samsung"])
        brand.pack(side="left",padx=(5,18))
        ttk.Label(header,text="Model:").pack(side="left")
        self.model_label=ttk.Label(header,text="Connect a device to identify model")
        self.model_label.pack(side="left",padx=6)
        self.status=ttk.Label(header,text="ADB: checking…")
        self.status.pack(side="right")

        main=ttk.Frame(self); main.pack(fill="both",expand=True,padx=10,pady=(0,10))
        left=ttk.Frame(main); left.pack(side="left",fill="y",padx=(0,8))
        right=ttk.Frame(main); right.pack(side="left",fill="both",expand=True)

        modebox=ttk.LabelFrame(left,text="Connection mode",padding=9)
        modebox.pack(fill="x")
        ttk.Radiobutton(modebox,text="ADB",variable=self.mode_var,value="ADB",
                        command=self.mode_changed).pack(side="left",padx=8)
        ttk.Radiobutton(modebox,text="FASTBOOT (read-only)",variable=self.mode_var,value="FASTBOOT",
                        command=self.mode_changed).pack(side="left",padx=8)

        devicebox=ttk.LabelFrame(left,text="Connected devices",padding=10)
        devicebox.pack(fill="x",pady=7)
        self.device_combo=ttk.Combobox(devicebox,state="readonly",width=34)
        self.device_combo.pack(fill="x",pady=(0,7))
        ttk.Button(devicebox,text="Detect / Refresh",command=self.detect_current).pack(fill="x")

        opbox=ttk.LabelFrame(left,text="Operations",padding=11)
        opbox.pack(fill="both",expand=True,pady=5)
        ops=[
            "Read device information",
            "Scan firmware and kernel",
            "Check exact root compatibility",
            "Verify existing root (UID 0)",
            "Export diagnostic report",
        ]
        for item in ops:
            ttk.Radiobutton(opbox,text=item,variable=self.operation_var,value=item).pack(anchor="w",pady=8)
        ttk.Button(opbox,text="Process Operation",command=self.process).pack(fill="x",pady=(16,5))
        ttk.Button(opbox,text="FIRE",command=self.open_fire_module).pack(fill="x",pady=5)

        ttk.Button(opbox,text="Open selected upstream guide",command=self.open_upstream).pack(fill="x",pady=4)
        ttk.Label(opbox,text="No FRP / demo bypass\nNo factory reset\nNo bootloader unlock\nNo partition writes or flashing",
                  foreground="#f5c45b",justify="left").pack(anchor="w",pady=(20,4))

        devbox=ttk.LabelFrame(right,text="Device information",padding=7)
        devbox.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(devbox,columns=("property","value"),show="headings")
        self.tree.heading("property",text="Property")
        self.tree.heading("value",text="Detected value")
        self.tree.column("property",width=210,anchor="w")
        self.tree.column("value",width=600,anchor="w")
        self.tree.pack(fill="both",expand=True)

        logbox=ttk.LabelFrame(right,text="Live operation log",padding=7)
        logbox.pack(fill="both",expand=True,pady=(8,0))
        self.logview=tk.Text(logbox,height=12,bg="#101317",fg="#dce5ec",
                             insertbackground="white",font=("Consolas",9),
                             relief="flat",wrap="word",padx=9,pady=7)
        self.logview.pack(fill="both",expand=True)
        self.logview.tag_config("ok",foreground="#5bd18a")
        self.logview.tag_config("warn",foreground="#f5c45b")
        self.logview.tag_config("err",foreground="#ff7777")
        footer=ttk.Frame(self,padding=(12,5)); footer.pack(fill="x")
        ttk.Label(footer,text="USB ADB + FASTBOOT • Exact model/build/kernel matching • Diagnostic and upstream-guidance framework").pack(side="left")
        ttk.Button(footer,text="About / safety",command=self.about).pack(side="right")

    def log(self,msg,tag=None):
        self.logview.insert("end",msg+"\n",tag or ())
        self.logview.see("end")

    def refresh_tools(self):
        self.adb=shutil.which("adb")
        self.fastboot=shutil.which("fastboot")
        self.status.config(text=f"ADB: {'available' if self.adb else 'missing'} | FASTBOOT: {'available' if self.fastboot else 'missing'}")
        if not self.adb: self.log("adb.exe not found. Install Android SDK Platform-Tools and add folder to PATH.","warn")
        if not self.fastboot: self.log("fastboot.exe not found. FASTBOOT detection will be unavailable.","warn")

    def mode_changed(self):
        if self.mode_var.get()=="ADB": self.detect_adb(silent=False)
        else: self.detect_fastboot()

    def detect_current(self):
        self.refresh_tools()
        if self.mode_var.get()=="ADB": self.detect_adb(silent=False)
        else: self.detect_fastboot()

    def detect_adb(self,silent=False):
        if not self.adb: self.refresh_tools()
        if not self.adb: return
        try:
            r=run([self.adb,"devices"])
            rows=[]
            for line in r.stdout.splitlines()[1:]:
                p=line.split()
                if len(p)>=2: rows.append((p[0],p[1]))
            self.device_combo["values"]=[f"{s} [{state}]" for s,state in rows]
            ready=[s for s,state in rows if state=="device"]
            if ready:
                self.serial=ready[0]; self.device_combo.current(0)
                self.log(f"ADB device connected: {self.serial}","ok")
                if not silent: self.log("ADB authorization: OK","ok")
            elif rows:
                self.serial=None
                self.log("Device detected but unauthorized/offline. Unlock phone and accept USB debugging prompt.","warn")
            else:
                self.serial=None
                if not silent: self.log("No ADB device found. Check cable, USB debugging and OEM USB driver.","warn")
        except Exception as e: self.log(f"ADB detection error: {e}","err")

    def detect_fastboot(self):
        if not self.fastboot:
            self.log("fastboot.exe missing. Install Android SDK Platform-Tools.","err"); return
        try:
            r=run([self.fastboot,"devices"])
            lines=r.stdout.strip()
            self.log("FASTBOOT scan: "+("device found" if lines else "no device found"),
                     "ok" if lines else "warn")
            if lines: self.log(lines)
            self.log("Read-only scan only. No unlock, erase, flash or partition command is available.")
        except Exception as e: self.log(f"FASTBOOT scan error: {e}","err")

    def selected_serial(self):
        val=self.device_combo.get().strip()
        return val.split(" [",1)[0] if val else self.serial

    def shell(self,*args,timeout=18):
        serial=self.selected_serial()
        if not self.adb or not serial: raise RuntimeError("No authorized ADB device selected.")
        r=run([self.adb,"-s",serial,"shell",*args],timeout=timeout)
        if r.returncode and not r.stdout.strip(): raise RuntimeError(r.stderr.strip() or "ADB shell command failed")
        return r.stdout.strip()

    def process(self):
        op=self.operation_var.get()
        if self.mode_var.get()=="FASTBOOT":
            self.detect_fastboot(); return
        if op=="Export diagnostic report": self.export_report(); return
        if not self.selected_serial():
            self.detect_adb()
            if not self.selected_serial(): return
        threading.Thread(target=self._process_worker,args=(op,),daemon=True).start()

    def _process_worker(self,op):
        try:
            self.after(0,lambda:self.log(f"\n{op} started…"))
            if op=="Read device information": self.scan(False)
            elif op=="Scan firmware and kernel": self.scan(True)
            elif op=="Check exact root compatibility":
                self.scan(True); self.check_profile()
            elif op=="Verify existing root (UID 0)": self.verify_root()
        except Exception as e: self.after(0,lambda:self.log(f"Operation failed: {e}","err"))

    def scan(self,with_kernel):
        info={}
        self.after(0,lambda:self.log("Reading device system information…"))
        for label,prop in PROPS:
            try: value=self.shell("getprop",prop)
            except Exception: value=""
            info[label]=safe_text(value)
            self.after(0,lambda l=label,v=value:self.log(f"{l}: {safe_text(v)}"))
        if with_kernel:
            info["Full kernel release"]=safe_text(self.shell("uname","-r"))
            info["Page size"]=safe_text(self.shell("getconf","PAGE_SIZE"))
            self.after(0,lambda:self.log("Full kernel release: "+info["Full kernel release"]))
            self.after(0,lambda:self.log("Page size: "+info["Page size"]))
        self.info=info
        self.after(0,self.populate_tree)
        self.after(0,lambda:self.log("Device scan completed.","ok"))

    def populate_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for k,v in self.info.items(): self.tree.insert("","end",values=(k,v))
        model=self.info.get("Model","Unknown")
        self.model_label.config(text=model)
        if self.brand_var.get()=="Auto detect":
            m=(self.info.get("Manufacturer","")+" "+self.info.get("Brand","")).lower()
            if "oppo" in m: self.brand_var.set("OPPO")
            elif "vivo" in m: self.brand_var.set("vivo")
            elif "oneplus" in m: self.brand_var.set("OnePlus")
            elif "samsung" in m: self.brand_var.set("Samsung")

    def check_profile(self):
        pinfo=self.info
        kernel=pinfo.get("Full kernel release","")
        model=pinfo.get("Model","")
        device=pinfo.get("Device codename","")
        build=pinfo.get("Build ID","")
        brand=self.brand_var.get()
        matches=[]
        for p in self.profiles.get("profiles",[]):
            exact=(p.get("brand","").lower()==brand.lower() and
                   p.get("model")==model and p.get("device")==device and
                   p.get("build_id")==build and p.get("kernel_release")==kernel)
            if exact and p.get("status")=="verified": matches.append(p)
        if matches:
            self.profile=matches[0]
            self.log("EXACT VERIFIED PROFILE MATCH","ok")
            self.log("Loader: "+self.profile.get("loader","Not specified"))
            self.log("Upstream guide: "+self.profile.get("upstream_url",""))
            self.log("Method: "+self.profile.get("method",""))
            self.log("Review upstream instructions and release signatures before use.")
        else:
            self.profile=None
            self.log("NO EXACT VERIFIED PROFILE FOUND.","warn")
            self.log(f"Detected: {brand} | {model} | {device} | {build} | {kernel}")
            self.log("Android version or brand match alone is not sufficient. Do not use a nearby profile.")

    def verify_root(self):
        try:
            out=self.shell("su","-c","id",timeout=12)
            if "uid=0(root)" in out:
                self.after(0,lambda:self.log("Root verification: UID 0 CONFIRMED — "+out,"ok"))
            else:
                self.after(0,lambda:self.log("Root not confirmed. su response: "+(out or "(empty)"),"warn"))
        except Exception as e:
            self.after(0,lambda:self.log("Root verification unavailable: "+str(e),"warn"))

    def open_upstream(self):
        if not self.profile:
            messagebox.showinfo("No verified profile","Run exact compatibility check first. No matching verified profile is currently selected.")
            return
        url=self.profile.get("upstream_url","")
        if url.startswith("https://"): webbrowser.open(url)
        else: messagebox.showwarning("Invalid URL","Profile does not contain a valid HTTPS upstream URL.")

    def export_report(self):
        if not self.info:
            messagebox.showinfo("No device data","Scan a device first."); return
        path=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON report","*.json")])
        if not path: return
        report={"tool":APP_TITLE,"created":datetime.now().isoformat(timespec="seconds"),
                "device_serial":self.selected_serial(),"properties":self.info,
                "profile_match":self.profile.get("loader") if self.profile else None,
                "safety_note":"Diagnostics only. No bootloader unlock, FRP action, exploit execution, partition write or flashing was performed."}
        with open(path,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
        messagebox.showinfo("Report saved","Diagnostic report exported.")

    def open_fire_module(self):
        win = tk.Toplevel(self)
        win.title("FIRE - Device Diagnostics")
        win.geometry("760x560")
        win.minsize(620, 440)

        header = ttk.Frame(win, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="FIRE",
                  font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, text="ADB Diagnostics & Recovery Guidance",
                  foreground="#5bd18a").pack(side="left", padx=15)

        info = ttk.LabelFrame(win, text="Device connection", padding=10)
        info.pack(fill="x", padx=12, pady=5)

        device_label = ttk.Label(info, text="Checking ADB device...")
        device_label.pack(anchor="w")

        output_box = ttk.LabelFrame(win, text="Diagnostic output", padding=8)
        output_box.pack(fill="both", expand=True, padx=12, pady=8)

        output = tk.Text(
            output_box, bg="#101317", fg="#dce5ec",
            insertbackground="white", font=("Consolas", 10),
            wrap="word", relief="flat", padx=9, pady=8
        )
        output.pack(fill="both", expand=True)

        def write(text):
            output.insert("end", str(text) + "\n")
            output.see("end")

        def get_device():
            if not self.adb:
                self.refresh_tools()
            if not self.adb:
                device_label.config(text="ADB unavailable")
                write("Install Android SDK Platform-Tools first.")
                return None

            self.detect_adb(silent=True)
            serial = self.selected_serial()

            if not serial:
                device_label.config(text="No authorized ADB device")
                write("No authorized device. Check USB debugging and authorization.")
                return None

            device_label.config(text="Connected: " + serial)
            return serial

        def check(commands):
            serial = get_device()
            if not serial:
                return

            write("\n--- Diagnostic started ---")
            for label, args in commands:
                try:
                    result = run(
                        [self.adb, "-s", serial, "shell", *args],
                        timeout=12
                    )
                    write(label + ":")
                    write(result.stdout.strip() or result.stderr.strip()
                          or "(No response)")
                except Exception as exc:
                    write(label + ": ERROR - " + str(exc))
            write("--- Diagnostic completed ---")

        def device_compatibility_summary():
            serial = get_device()
            write("\n========== DEVICE COMPATIBILITY & SECURITY SUMMARY ==========")

            if not serial:
                write("ADB Authorization: WARNING - No authorized device detected")
                write("Overall: INFO - Connect and authorize an ADB device.")
                write("============================================================")
                return

            def read_prop(prop):
                try:
                    result = run(
                        [self.adb, "-s", serial, "shell", "getprop", prop],
                        timeout=12
                    )
                    return result.stdout.strip()
                except Exception:
                    return ""

            manufacturer = read_prop("ro.product.manufacturer")
            model = read_prop("ro.product.model")
            android = read_prop("ro.build.version.release")
            sdk = read_prop("ro.build.version.sdk")
            patch = read_prop("ro.build.version.security_patch")
            locked = read_prop("ro.boot.flash.locked")
            vbmeta = read_prop("ro.boot.vbmeta.device_state")
            verified = read_prop("ro.boot.verifiedbootstate")

            write("Device: " + (manufacturer or "Unknown") + " " + (model or "Unknown"))
            write("Android Version: " + (android or "Unknown"))
            write("SDK Level: " + (sdk or "Unknown"))
            write("Security Patch: " + (patch or "Unknown"))
            write("ADB Authorization: PASS - Authorized device detected")

            if locked == "1" or vbmeta.lower() == "locked":
                write("Bootloader: PASS - Reports locked")
            elif locked == "0" or vbmeta.lower() == "unlocked":
                write("Bootloader: WARNING - Reports unlocked")
            else:
                write("Bootloader: INFO - Status unavailable")

            if verified.lower() == "green":
                write("Verified Boot: PASS - Green")
            elif verified:
                write("Verified Boot: WARNING - " + verified)
            else:
                write("Verified Boot: INFO - Status unavailable")

            if patch:
                write("Security Patch: INFO - Date reported by Android")
            else:
                write("Security Patch: WARNING - Date unavailable")

            if android and sdk.isdigit():
                write("Compatibility: INFO - Android version and SDK detected")
            else:
                write("Compatibility: WARNING - Version details incomplete")

            write("Overall: INFO - Diagnostic snapshot only; not a security certification.")
            write("Root compatibility is not established by these checks.")
            write("============================================================")

        def export_fire_report():
            serial = self.selected_serial() or "Not connected"
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = filedialog.asksaveasfilename(
                title="Save FIRE Diagnostic Report",
                initialfile="FIRE_Diagnostic_" + stamp + ".txt",
                defaultextension=".txt",
                filetypes=[("Text report", "*.txt")]
            )
            if not path:
                return

            report = (
                "UNIVERSAL ANDROID SERVICE TOOL - FIRE REPORT\n"
                "Generated: " + datetime.now().isoformat(timespec="seconds") + "\n"
                "ADB Device: " + serial + "\n"
                "============================================\n\n"
                + output.get("1.0", "end-1c")
                + "\n\nDiagnostics only. No FRP bypass or authentication changes.\n"
            )
            try:
                with open(path, "w", encoding="utf-8") as report_file:
                    report_file.write(report)
                messagebox.showinfo("Report saved", "FIRE report exported successfully.")
            except Exception as exc:
                messagebox.showerror("Export failed", str(exc))

        actions = ttk.LabelFrame(win, text="Available checks", padding=10)
        actions.pack(fill="x", padx=12, pady=5)

        ttk.Button(
            actions, text="Detect / Refresh Device",
            command=get_device
        ).pack(fill="x", pady=3)

        ttk.Button(
            actions, text="Read Device Information",
            command=lambda: check([
                ("Manufacturer", ["getprop", "ro.product.manufacturer"]),
                ("Brand", ["getprop", "ro.product.brand"]),
                ("Model", ["getprop", "ro.product.model"]),
                ("Android Version", ["getprop", "ro.build.version.release"]),
                ("Build ID", ["getprop", "ro.build.display.id"]),
                ("Security Patch", ["getprop", "ro.build.version.security_patch"]),
            ])
        ).pack(fill="x", pady=3)

        ttk.Button(
            actions, text="Security & Setup Diagnostics",
            command=lambda: check([
                ("ADB identity", ["id"]),
                ("Device provisioned", [
                    "settings", "get", "global", "device_provisioned"
                ]),
                ("User setup status", [
                    "settings", "get", "secure", "user_setup_complete"
                ]),
                ("Verified Boot State", [
                    "getprop", "ro.boot.verifiedbootstate"
                ]),
            ])
        ).pack(fill="x", pady=3)

        ttk.Button(
            actions, text="Device Compatibility & Security Summary",
            command=device_compatibility_summary
        ).pack(fill="x", pady=3)

        ttk.Button(
            actions, text="Export Diagnostic Report",
            command=export_fire_report
        ).pack(fill="x", pady=3)

        ttk.Button(
            actions, text="Clear Output",
            command=lambda: output.delete("1.0", "end")
        ).pack(fill="x", pady=3)

        write("FIRE module initialized.")
        write("Diagnostics only: no FRP bypass or authentication changes.")
        write("Public ADB properties cannot reliably confirm FRP lock status.")
        get_device()

    def about(self):
        messagebox.showinfo("Safety and scope",
            "This application provides USB ADB diagnostics, read-only FASTBOOT detection, exact profile matching and existing-root verification.\\n\\n"
            "It does not unlock bootloaders, erase FRP, bypass account locks, run exploit payloads, flash images or write partitions. "
            "Temporary-root support is device/build/kernel-specific. The profile database starts empty until exact upstream evidence is verified.")

if __name__=="__main__":
    UniversalTool().mainloop()
