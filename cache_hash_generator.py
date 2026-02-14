import os
import io
import hashlib
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from urllib.parse import quote

# ============================================================
# Cache Hash Generator
#
# This tool:
# - Generates reversed-MD5 cache filenames
# - Supports saving files individually or packed into a ZIP
# - Uses predefined Trackmania cache paths
# ============================================================

# File used to remember the last output directory
CONFIG_FILE = "last_dir.txt"

# Mapping between file type and encoded cache path
PATH_MAP = {
    "images": r"Skins%5cMediaTracker%5cImages%5c",
    "sounds": r"Skins%5cMediaTracker%5cSounds%5c",
    "music": r"Skins%5cChallengeMusics%5c",
    "mods": r"Skins%5cStadium%5cMod%5c",
    "advert": r"Skins%5cAny%5cAdvertisement%5c",
}

# Stores processed files as:
generated_files = []

# ============================================================
# Utility functions
# ============================================================

def md5_and_reverse_bytes(data: bytes):
    """
    Calculate MD5 hash of raw bytes and return:
    - Normal MD5 (hex, uppercase)
    - Reversed-byte MD5 (hex, uppercase)
    """
    md5 = hashlib.md5(data).hexdigest().upper()
    rev = bytes.fromhex(md5)[::-1].hex().upper()
    return md5, rev


def md5_and_reverse_file(path: str):
    """
    Read a file from disk and return its MD5 and reversed MD5.
    """
    with open(path, "rb") as f:
        return md5_and_reverse_bytes(f.read())


def encode_name(name: str) -> str:
    """
    URL-encode filename only if it contains non-ASCII characters.
    """
    return quote(name, safe="") if any(ord(c) > 127 for c in name) else name


def load_last_dir():
    """
    Load the last used directory from disk (if valid).
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            p = f.read().strip()
            if os.path.isdir(p):
                return p
    return None


def save_last_dir(path: str):
    """
    Save the last used directory to disk.
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(path)

# ============================================================
# Core processing logic
# ============================================================

def process_files(files):
    """
    Generate cache filenames for selected files
    and display them in the output box.
    """
    file_type = file_type_var.get()
    base_path = PATH_MAP[file_type]

    for file in files:
        _, rev = md5_and_reverse_file(file)
        name = encode_name(os.path.basename(file))

        # Final cache-style filename
        line = f"{rev}_{base_path}{name}"

        generated_files.append((file, line))
        output.insert(tk.END, line + "\n")


def save_single_mode():
    """
    Save each processed file individually using
    its generated cache filename.
    """
    folder = filedialog.askdirectory(initialdir=load_last_dir())
    if not folder:
        return

    for original, line in generated_files:
        out_path = os.path.join(folder, line)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        with open(original, "rb") as src, open(out_path, "wb") as dst:
            dst.write(src.read())

    save_last_dir(folder)
    messagebox.showinfo("Done", "Files saved successfully.")
    clear_all()


def save_pack_mode():
    """
    Pack all processed files into a ZIP file.
    The ZIP file itself is not hashed; internal files use hash-based names.
    """
    base_path = PATH_MAP[file_type_var.get()]
    zip_name = simpledialog.askstring("ZIP name", "Enter ZIP base name:")

    if not zip_name:
        return

    # Create ZIP in memory
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for original, line in generated_files:
            z.write(original, arcname=line)

    zip_bytes = buffer.getvalue()
    final_name = f"{zip_name}.zip"

    out = filedialog.asksaveasfilename(
        initialfile=final_name,
        defaultextension=".zip",
        filetypes=[("ZIP files", "*.zip")],
        initialdir=load_last_dir()
    )
    if not out:
        return

    with open(out, "wb") as f:
        f.write(zip_bytes)

    save_last_dir(os.path.dirname(out))
    messagebox.showinfo("Done", "Packed ZIP created.")
    clear_all()

def save_output():
    """
    Dispatch save logic depending on output mode.
    """
    if not generated_files:
        messagebox.showwarning("Empty", "No files processed.")
        return

    if output_mode.get() == "single":
        save_single_mode()
    else:
        save_pack_mode()


def clear_all():
    """
    Clear generated file list and output text box.
    """
    generated_files.clear()
    output.delete("1.0", tk.END)

# ============================================================
# UI setup
# ============================================================

root = tk.Tk()
root.title("Cache Hash Generator")
root.geometry("720x560")

# Output mode selection
mode_frame = tk.LabelFrame(root, text="Output Mode")
mode_frame.pack(fill="x", padx=15, pady=10)

output_mode = tk.StringVar(value="single")
tk.Radiobutton(mode_frame, text="Single files", variable=output_mode, value="single").pack(side="left", padx=10)
tk.Radiobutton(mode_frame, text="Pack selection into ZIP", variable=output_mode, value="pack").pack(side="left", padx=10)

# Type selection
type_frame = tk.LabelFrame(root, text="Type")
type_frame.pack(fill="x", padx=15, pady=5)

file_type_var = tk.StringVar(value="images")
file_type_frame = tk.Frame(type_frame)

for k in PATH_MAP:
    tk.Radiobutton(
        file_type_frame,
        text=k.capitalize(),
        variable=file_type_var,
        value=k
    ).pack(side="left", padx=8)

file_type_frame.pack(anchor="w")

def update_type_ui(*_):
    """
    The full type selector is always visible.
    """
    pass

output_mode.trace_add("write", update_type_ui)

# Buttons
btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

def select_files():
    """
    Open file picker and process selected files.
    """
    files = filedialog.askopenfilenames()
    if files:
        process_files(files)

tk.Button(btn_frame, text="Select Files", command=select_files, width=14).pack(side="left", padx=5)
tk.Button(btn_frame, text="Save", command=save_output, width=14).pack(side="left", padx=5)
tk.Button(btn_frame, text="Clear", command=clear_all, width=12).pack(side="left", padx=5)
tk.Button(btn_frame, text="Close", command=root.destroy, width=10).pack(side="left", padx=5)

# Output display
output = tk.Text(root, font=("Courier", 9))
output.pack(fill="both", expand=True, padx=15, pady=10)

root.mainloop()
