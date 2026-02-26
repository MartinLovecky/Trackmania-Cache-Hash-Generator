# Cache Hash Generator

**Version 2.0.0 is a complete rewrite and not backward compatible.**
The old version is available in the [`legacy-v1`](https://github.com/MartinLovecky/Trackmania-Cache-Hash-Generator/tree/legacy-v1) branch or via tag [`v1-final`](https://github.com/MartinLovecky/Trackmania-Cache-Hash-Generator/releases/tag/v1-final).

A Tkinter-based utility for generating **Trackmania cache-style filenames** using **reversed MD5 hashes**, now with **automated folder processing**, **parallel threading**, and improved UI.

---

## Features

* Recursively processes **all files in a selected folder**
* Generates **reversed-byte MD5 cache filenames**
* GUI shows real-time progress with output logging
* Supports saving processed files into a `[Generated]<FolderName>` output folder
* Remembers **last base folder** and **last save directory**
* Can open or choose the **Trackmania cache folder** directly from GUI
* Skips ignored extensions: `.txt`, `.loc`
* Multi-threaded processing for faster performance
* Safety handling for double hashes in filenames
* URL-encodes non-ASCII path components automatically

---

## How It Works

### Hashing

* Each file is hashed using **MD5**
* The MD5 bytes are **reversed**
* Reversed MD5 is prepended to the relative cache path
* Resulting filename format:

```
<REVERSED_MD5>_<URL-encoded cache path>
```

**Example output filename:**

```
ABCDEF1234567890ABCDEF1234567890_Skins%5cMediaTracker%5cImages%5cmyimage.png
```

---

### Folder Processing

* Select a **base folder** to process all files recursively
* Real-time **status updates** and output log in the GUI
* Can **stop processing** at any time
* Files are stored in:

```
[Generated]<BaseFolderName>\
```

* Existing folder structures are preserved

---

### Saving Files

* Click **Save** to export processed files
* GUI asks for an output folder
* Original folder name is prepended with `[Generated]`
* Only successfully processed files are saved

---

### Cache Folder

* Click **Open Cache** to open or select your Trackmania cache folder
* Path is remembered for future sessions
* Automatically opens the folder in Explorer / Finder / Nautilus

---

## Usage

### Requirements

* Python 3.8+
* Standard library only (no external dependencies)

### Run

```bash
python cache_hash_generator.py
```

* Use the GUI buttons:

  * **Open Cache** – open or select cache folder
  * **Process Folder** – recursively process files in a base folder
  * **Save** – save processed files
  * **Clear** – clear log/output
  * **Close** – exit the app

---

## Supported Cache Paths (Auto-detected)

| Type          | Cache Path                   |
| ------------- | ---------------------------- |
| Images        | `Skins\MediaTracker\Images\` |
| Sounds        | `Skins\MediaTracker\Sounds\` |
| Music         | `Skins\ChallengeMusics\`     |
| Mods          | `Skins\Stadium\Mod\`         |
| Advertisement | `Skins\Any\Advertisement\`   |

*(Paths are URL-encoded internally to match Trackmania cache format.)*

---

## Notes

* Multi-threaded processing adapts to your CPU cores
* Skipped extensions (`.txt`, `.loc`) will not be processed
* Double-hash safety ensures filenames are not duplicated
* GUI updates are handled via a queue to keep the interface responsive
