import os
import io
import subprocess
import sys
import hashlib
import zipfile
import tkinter as tk
import concurrent.futures
from tkinter import filedialog, messagebox, simpledialog
from urllib.parse import quote
from pathlib import Path
import threading
import queue

# ============================================================
# Cache Hash Generator - Automated Version
#
# This tool:
# - Takes a base folder containing game files
# - Recursively processes all files
# - Generates reversed-MD5 cache filenames based on file content
# ============================================================

CONFIG_FILE = "last_dir.txt"
IGNORED_EXTENSIONS = {".txt", ".loc"}
processed_files = []
processing_active = False
ui_queue = queue.Queue()

# ============================================================
# CONFIG HANDLING
# ============================================================

def load_config():
    config = {"save_path": None, "base_path": None, "cache_path": None}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    if os.path.isdir(v):
                        config[k] = v
    return config

def save_config_value(key, value):
    config = load_config()
    config[key] = value
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        for k, v in config.items():
            if v:
                f.write(f"{k}={v}\n")

def get_save_dir():
    return load_config().get("save_path")

def get_base_dir():
    return load_config().get("base_path")

def get_cache_dir():
    return load_config().get("cache_path")

# ============================================================
# SAVE OUTPUT FIXED
# ============================================================

def save_output():
    if not processed_files:
        messagebox.showwarning("Empty", "No files processed yet.")
        return

    folder = filedialog.askdirectory(
        title="Select Output Folder",
        initialdir=get_save_dir()
    )

    if not folder:
        return

    base_folder = get_base_dir()
    if not base_folder or not os.path.isdir(base_folder):
        base_folder_name = "Output"
    else:
        base_folder_name = os.path.basename(base_folder.rstrip("/\\"))

    out_root = os.path.join(folder, f"[Generated]{base_folder_name}")
    os.makedirs(out_root, exist_ok=True)

    saved = 0

    # FIX: unpack only 3 items per tuple
    for original, cache_path, _ in processed_files:
        if cache_path.startswith("ERROR"):
            continue

        out_path = os.path.join(out_root, cache_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(original, "rb") as src, open(out_path, "wb") as dst:
            dst.write(src.read())

        saved += 1

    save_config_value("save_path", folder)
    messagebox.showinfo("Done", f"Saved {saved} files.")

# ============================================================
# OPEN FOLDER
# ============================================================

def open_folder(path):
    if not os.path.isdir(path):
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["nautilus", "--no-desktop", path])
    except Exception as e:
        messagebox.showerror("Error", f"Cannot open folder:\n{e}")

def open_or_choose_cache():
    path = get_cache_dir()
    if path and os.path.isdir(path):
        open_folder(path)
        return
    folder = filedialog.askdirectory(title="Select Trackmania Cache Folder")
    if not folder:
        return
    save_config_value("cache_path", folder)
    messagebox.showinfo("Cache folder saved", folder)
    open_folder(folder)

# ============================================================
# UTILS
# ============================================================

def md5_and_reverse_file(path, chunk_size=1024 * 1024):
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    md5_hex = md5.hexdigest().upper()
    return bytes.fromhex(md5_hex)[::-1].hex().upper()

def encode_component(component):
    return quote(component, safe="") if any(ord(c) > 127 for c in component) else component

# ============================================================
# CORE LOGIC
# ============================================================

def extract_cache_path(full_path, base_path, rev_md5=None):
    full = Path(full_path)
    base = Path(base_path)
    rel_parts = full.relative_to(base).parts

    # Skip first part if it matches the hash (already included)
    if rev_md5 and rel_parts:
        if rel_parts[0].upper() == rev_md5:
            rel_parts = rel_parts[1:]

    encoded = [encode_component(p) for p in rel_parts]
    cache_path = "%5c".join(encoded)
    return cache_path

def process_single_file(path, base):
    try:
        rev_md5 = md5_and_reverse_file(path)
        cache_sub = extract_cache_path(path, base, rev_md5)
        cache_name = f"{rev_md5}_{cache_sub}"
        # Safety: if double hash appears, strip second occurrence
        if cache_name.startswith(f"{rev_md5}_{rev_md5}_"):
            cache_name = cache_name.replace(f"{rev_md5}_{rev_md5}_", f"{rev_md5}_", 1)
        display = cache_name
        return (path, cache_name, display)
    except Exception as e:
        return (path, f"ERROR:{e}", f"ERROR {path}: {e}")

# ============================================================
# PARALLEL WORKER
# ============================================================

def process_folder(base_folder):
    global processed_files, processing_active

    processed_files.clear()
    all_files = []

    for walk_root, _, files in os.walk(base_folder):
        for f in files:
            if Path(f).suffix.lower() in IGNORED_EXTENSIONS:
                continue
            all_files.append(os.path.join(walk_root, f))

    total = len(all_files)
    done = 0

    def worker(p):
        if not processing_active:
            return None
        return process_single_file(p, base_folder)

    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(worker, f) for f in all_files]
        for future in concurrent.futures.as_completed(futures):
            if not processing_active:
                break
            result = future.result()
            if not result:
                continue
            processed_files.append(result)
            done += 1
            ui_queue.put({"type": "output", "text": result[2]})
            if done % 20 == 0:
                ui_queue.put({"type": "status", "text": f"Processed {done}/{total}"})

    processing_active = False
    ui_queue.put({"type": "status", "text": f"Complete! {done} files"})
    ui_queue.put({"type": "done"})

# ============================================================
# UI QUEUE PROCESSOR
# ============================================================

def process_ui_queue():
    try:
        while True:
            msg = ui_queue.get_nowait()
            if msg["type"] == "status":
                status_label.config(text=msg["text"])
            elif msg["type"] == "output":
                output.insert(tk.END, msg["text"] + "\n")
                output.see(tk.END)
            elif msg["type"] == "done":
                process_button.config(state="normal")
                save_button.config(state="normal")
                stop_button.config(state="disabled")
    except queue.Empty:
        pass
    root.after(50, process_ui_queue)

# ============================================================
# UI ACTIONS
# ============================================================

def start_processing():
    global processing_active
    base_folder = filedialog.askdirectory(title="Select Base Folder", initialdir=get_base_dir())
    if not base_folder:
        return
    save_config_value("base_path", base_folder)
    processing_active = True
    process_button.config(state="disabled")
    save_button.config(state="disabled")
    stop_button.config(state="normal")
    thread = threading.Thread(target=process_folder, args=(base_folder,), daemon=True)
    thread.start()

def clear_all():
    processed_files.clear()
    output.delete("1.0", tk.END)
    status_label.config(text="Ready")

# ============================================================
# UI SETUP
# ============================================================

root = tk.Tk()
root.title("Cache Hash Generator - Automated")
root.geometry("900x650")

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="Open Cache", command=open_or_choose_cache, width=14).pack(side="left", padx=5)
tk.Button(btn_frame, text="Process Folder", command=start_processing, width=14).pack(side="left", padx=5)
tk.Button(btn_frame, text="Save", command=save_output, width=10, state="disabled").pack(side="left", padx=5)
tk.Button(btn_frame, text="Clear", command=clear_all, width=10).pack(side="left", padx=5)
tk.Button(btn_frame, text="Close", command=root.destroy, width=10).pack(side="left", padx=5)


status_label = tk.Label(root, text="Ready", anchor="w")
status_label.pack(fill="x", padx=15)

frame = tk.Frame(root)
frame.pack(fill="both", expand=True, padx=15, pady=10)

scrollbar = tk.Scrollbar(frame)
scrollbar.pack(side="right", fill="y")

output = tk.Text(frame, font=("Courier", 9), yscrollcommand=scrollbar.set, wrap="none")
output.pack(side="left", fill="both", expand=True)

scrollbar.config(command=output.yview)

# Start queue processor
process_ui_queue()

root.mainloop()