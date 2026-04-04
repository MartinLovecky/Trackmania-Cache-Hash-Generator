import os
import sys
import subprocess
import hashlib
import zipfile
import tempfile
import shutil
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from urllib.parse import quote
import concurrent.futures
import threading
import queue

# ============================================================
# Cache Hash Generator
# ============================================================

APP_NAME = "CacheHashGenerator"
IGNORED_EXTENSIONS = {".txt", ".loc"}

processed_files = []
processing_active = False
ui_queue = queue.Queue()
temp_dir = None
input_is_zip = False
start_time = 0

# ============================================================
# CONFIG HANDLING
# ============================================================

def get_config_dir():
    if sys.platform.startswith("win"):
        base = os.getenv("APPDATA")
    elif sys.platform.startswith("darwin"):
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
    cfg = Path(base) / APP_NAME
    cfg.mkdir(parents=True, exist_ok=True)
    return cfg

CONFIG_DIR = get_config_dir()
CONFIG_FILE = CONFIG_DIR / "last_dir.txt"

def load_config():
    config = {"save_path": None, "base_path": None}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        if os.path.isdir(v):
                            config[k] = v
        except Exception:
            pass
    return config

def save_config_value(key, value):
    try:
        config = load_config()
        config[key] = value
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            for k, v in config.items():
                if v:
                    f.write(f"{k}={v}\n")
    except PermissionError:
        messagebox.showerror("Permission Error", "Cannot save configuration file.")

def get_save_dir(): return load_config().get("save_path")
def get_base_dir(): return load_config().get("base_path")

# ============================================================
# UTILITIES
# ============================================================

def md5_and_reverse_file(path, chunk_size=1024*1024):
    h = hashlib.md5(usedforsecurity=False)
    with open(path, "rb", buffering=chunk_size) as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.digest()[::-1].hex().upper()

def encode_component(component):
    return quote(component, safe="") if any(ord(c) > 127 for c in component) else component

def extract_cache_path(full_path, base_path, rev_md5=None):
    full = Path(full_path)
    base = Path(base_path)
    rel_parts = full.relative_to(base).parts
    if rev_md5 and rel_parts and rel_parts[0].upper() == rev_md5:
        rel_parts = rel_parts[1:]
    return "%5c".join(encode_component(p) for p in rel_parts)

def process_single_file(args):
    path, base = args
    try:
        rev_md5 = md5_and_reverse_file(path)
        cache_sub = extract_cache_path(path, base, rev_md5)
        cache_name = f"{rev_md5}_{cache_sub}"
        if cache_name.startswith(f"{rev_md5}_{rev_md5}_"):
            cache_name = cache_name.replace(f"{rev_md5}_{rev_md5}_", f"{rev_md5}_", 1)
        return (path, cache_name, cache_name)
    except Exception as e:
        return (path, f"ERROR:{e}", f"ERROR {path}: {e}")

# ============================================================
# FILE COLLECTION
# ============================================================

def collect_files_from_path(input_path):
    all_files = []
    input_path = Path(input_path)
    global temp_dir, input_is_zip

    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        temp_dir = tempfile.TemporaryDirectory(prefix="cache_hash_")
        base_dir = temp_dir.name
        with zipfile.ZipFile(input_path, 'r') as zf:
            for info in zf.infolist():
                if info.is_dir() or Path(info.filename).suffix.lower() in IGNORED_EXTENSIONS:
                    continue
                zf.extract(info, path=base_dir)
        input_is_zip = True
        for p in Path(base_dir).rglob("*"):
            if p.is_file() and p.suffix.lower() not in IGNORED_EXTENSIONS:
                all_files.append(str(p))
        return all_files, base_dir
    else:
        input_is_zip = False
        for p in Path(input_path).rglob("*"):
            if p.is_file() and p.suffix.lower() not in IGNORED_EXTENSIONS:
                all_files.append(str(p))
        return all_files, str(input_path)

# ============================================================
# PROCESSING
# ============================================================

def process_folder(base_folder):
    global processed_files, processing_active, start_time
    processed_files.clear()
    start_time = time.time()

    try:
        all_files, actual_base = collect_files_from_path(base_folder)
    except Exception as e:
        ui_queue.put({"type":"status","text":f"Error reading input: {e}"})
        processing_active = False
        ui_queue.put({"type":"done"})
        return

    total = len(all_files)
    done = 0

    def worker_args():
        for f in all_files:
            if not processing_active:
                break
            yield (f, actual_base)

    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        for future in executor.map(process_single_file, worker_args()):
            if not processing_active:
                break
            processed_files.append(future)
            done += 1
            ui_queue.put({"type":"progress", "current": done, "total": total, "file": future[2]})

    processing_active = False
    elapsed = time.time() - start_time
    ui_queue.put({"type":"done", "elapsed": elapsed})

# ============================================================
# SAVE FUNCTIONS
# ============================================================

def save_output_as_folder():
    if not processed_files:
        messagebox.showwarning("Empty","No files processed yet.")
        return
    folder = filedialog.askdirectory(title="Select Output Folder", initialdir=get_save_dir())
    if not folder:
        return

    base_path = get_base_dir()
    base_name = os.path.basename(base_path.rstrip("/\\")) if base_path and os.path.isdir(base_path) else "Output"
    out_root = Path(folder) / f"[Generated]{base_name}"
    out_root.mkdir(parents=True, exist_ok=True)

    saved = 0
    for original, cache_path, _ in processed_files:
        if cache_path.startswith("ERROR"): continue
        dest = out_root / cache_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, dest)
        saved += 1

    save_config_value("save_path", folder)
    messagebox.showinfo("Done", f"Saved {saved} files to folder:\n{out_root}")

def save_output_as_zip():
    if not processed_files:
        messagebox.showwarning("Empty","No files processed yet.")
        return
    zip_path = filedialog.asksaveasfilename(title="Save as Zip", defaultextension=".zip",
                                            filetypes=[("Zip archives","*.zip")],
                                            initialdir=get_save_dir())
    if not zip_path:
        return
    saved = 0
    try:
        with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as zf:
            for original, cache_path, _ in processed_files:
                if cache_path.startswith("ERROR"): continue
                zf.write(original, arcname=cache_path)
                saved += 1
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create zip:\n{e}")
        return
    save_config_value("save_path", str(Path(zip_path).parent))
    messagebox.showinfo("Done", f"Saved {saved} files to zip:\n{zip_path}")

# ============================================================
# UI & HELPERS
# ============================================================

def start_processing():
    global processing_active, temp_dir, input_is_zip
    if temp_dir:
        try: temp_dir.cleanup()
        except: pass
        temp_dir = None
    input_path = filedialog.askopenfilename(title="Select Folder or Zip File", initialdir=get_base_dir(),
                                            filetypes=[("Zip files","*.zip"), ("All files","*.*")])
    if not input_path: return
    if Path(input_path).is_file() and Path(input_path).suffix.lower()==".zip":
        base_folder = input_path
    else:
        base_folder = filedialog.askdirectory(title="Select Base Folder", initialdir=get_base_dir())
        if not base_folder: return
    save_config_value("base_path", base_folder)
    processing_active = True
    process_button.config(state="disabled")
    save_button.config(state="disabled")
    save_zip_button.config(state="disabled")
    cancel_button.config(state="normal")
    threading.Thread(target=process_folder, args=(base_folder,), daemon=True).start()

def cancel_processing():
    global processing_active
    processing_active = False
    progress_label.config(text="Cancelling...", foreground="#e67e22")

def clear_all():
    global processed_files, temp_dir, input_is_zip
    processed_files.clear()
    progress_var.set(0)
    progress_label.config(text="Ready", foreground="#2c3e50")
    if temp_dir:
        try: temp_dir.cleanup()
        except: pass
        temp_dir = None
    input_is_zip = False

def on_closing():
    if temp_dir:
        try: temp_dir.cleanup()
        except: pass
    root.destroy()

def process_ui_queue():
    try:
        while True:
            msg = ui_queue.get_nowait()
            if msg["type"]=="progress":
                progress_label.config(text=f"{msg['current']}/{msg['total']} - {msg['file']}", foreground="#2c3e50")
                progress_var.set(msg['current']/msg['total']*100)
            elif msg["type"]=="done":
                progress_label.config(text=f"Complete! {len(processed_files)} files in {msg.get('elapsed',0):.1f}s", foreground="#27ae60")
                progress_var.set(100)
                process_button.config(state="normal")
                save_button.config(state="normal")
                save_zip_button.config(state="normal")
                cancel_button.config(state="disabled")
    except queue.Empty:
        pass
    root.after(50, process_ui_queue)

# ============================================================
# GUI SETUP
# ============================================================

def setup_modern_style():
    style = ttk.Style()
    available_themes = style.theme_names()
    if 'clam' in available_themes:
        style.theme_use('clam')
    elif 'alt' in available_themes:
        style.theme_use('alt')
    
    # Colors
    bg_color = "#f5f6fa"
    fg_color = "#2c3e50"
    accent_color = "#3498db"
    accent_hover = "#2980b9"
    button_bg = "#ecf0f1"
    disabled_fg = "#bdc3c7"
    
    root.configure(bg=bg_color)
    style.configure("TFrame", background=bg_color)
    style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
    style.configure("TButton", background=button_bg, foreground=fg_color, borderwidth=0, focusthickness=0,
                    padding=(12, 6), font=("Segoe UI", 9, "bold"))
    style.map("TButton",
              background=[("active", accent_hover), ("pressed", accent_color)],
              foreground=[("active", "white"), ("disabled", disabled_fg)],
              relief=[("pressed", "sunken")])
    # Disabled button style
    style.map("TButton", foreground=[("disabled", disabled_fg)], background=[("disabled", button_bg)])
    
    # Progress bar
    style.configure("TProgressbar", background=accent_color, troughcolor="#e0e0e0", borderwidth=0,
                    thickness=12)
    
    # Main frame (card-like)
    style.configure("Card.TFrame", background="white", relief="flat", borderwidth=1)
    
    return style

# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Cache Hash Generator")
    root.geometry("600x200")
    root.minsize(600, 200)
    # Center window
    root.eval('tk::PlaceWindow . center')
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    setup_modern_style()
    
    # Main container with card-like appearance
    main_frame = ttk.Frame(root, style="Card.TFrame", padding=20)
    main_frame.pack(fill="both", expand=True, pady=15)
    
    # Button bar (without Open Cache)
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill="x", pady=(0, 15))
    
    process_button = ttk.Button(btn_frame, text="📁 Process Folder/Zip", command=start_processing, width=20)
    process_button.pack(side="left", padx=2)
    
    save_button = ttk.Button(btn_frame, text="💾 Save as Folder", command=save_output_as_folder, state="disabled", width=15)
    save_button.pack(side="left", padx=2)
    
    save_zip_button = ttk.Button(btn_frame, text="🗜️ Save as Zip", command=save_output_as_zip, state="disabled", width=15)
    save_zip_button.pack(side="left", padx=2)
    
    cancel_button = ttk.Button(btn_frame, text="❌ Cancel", command=cancel_processing, state="disabled", width=12)
    cancel_button.pack(side="left", padx=2)
    
    # Progress section
    progress_frame = ttk.Frame(main_frame)
    progress_frame.pack(fill="x", pady=2)
    
    progress_label = ttk.Label(progress_frame, text="Ready", font=("Segoe UI", 10, "italic"))
    progress_label.pack(anchor="w")
    
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, style="TProgressbar")
    progress_bar.pack(fill="x", pady=(8, 0))
    
    # Status bar hint
    status_hint = ttk.Label(main_frame, text="Supports folders or ZIP files | Excludes .txt & .loc files", 
                            font=("Segoe UI", 8), foreground="#7f8c8d")
    status_hint.pack(side="bottom", fill="x", pady=(15, 0))
    
    root.after(50, process_ui_queue)
    root.mainloop()