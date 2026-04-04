# Cache Hash Generator

## Version 2.1.0 

A Tkinter‑based utility for generating **Trackmania cache‑style filenames** using **reversed MD5 hashes**.  
Supports processing entire folders or zip archives, multi‑threading, and an updated UI.

---

## Features

- Process a **folder** or a **zip file** containing game files
- Generate reversed‑MD5 Trackmania cache filenames
- Real‑time GUI progress indicator
- Save output as a **folder** or **zip archive**
- Remembers last used input path and save location
- Skips ignored extensions: `.txt`, `.loc`
- Multi‑threaded processing (adapts to CPU cores)
- Automatically URL‑encodes non‑ASCII path components
- Cancel processing at any time

---

## How It Works

### Hashing

- Each file is hashed using **MD5** (with `usedforsecurity=False` for compatibility)
- MD5 bytes are **reversed**
- The reversed MD5 hash is prepended to the relative cache path
- Final filename format:

```
<REVERSED_MD5>_<URL‑encoded cache path>
```

**Example:**

```
ABCDEF1234567890ABCDEF1234567890_Skins%5cMediaTracker%5cImages%5cmyimage.png
```

---

## Folder & Zip Processing

### Folder Processing

- Select a **base folder** – all files are scanned recursively
- Real‑time status updates show current file and progress
- Processing can be **stopped at any time** via the Cancel button
- Output files are stored in:

```
[Generated]<BaseFolderName>\
```

- Original directory structure is preserved

### Zip Input

- Selecting a `.zip` file automatically extracts it to a temporary directory
- Temporary data is auto‑cleaned when:
  - closing the application, or
  - starting a new processing job

---

## Saving Files

### Save as Folder

Creates a folder named `[Generated]<BaseFolderName>` in the chosen output directory.  
All generated files are copied into this folder, preserving the cache‑style naming and folder hierarchy.

### Save as Zip

Packs all generated files into a single `.zip` archive.  
Only successfully processed files are included.

---

## Usage

### Requirements

- Python **3.10+** (standard library only – no external dependencies)

### Run

```bash
python cache_hash_generator.py
```

### Steps

1. Click **Process Folder/Zip** and select a folder or `.zip` file
2. Wait for processing to complete (progress updates in real time)
3. Choose **Save as Folder** or **Save as Zip**
4. (Optional) Process another folder or zip

### GUI Buttons

- **Process Folder/Zip** – start processing (supports both folders and zip files)
- **Save as Folder** – export generated files to a folder (enabled after processing)
- **Save as Zip** – export generated files as a zip archive (enabled after processing)
- **Cancel** – stop the current processing job

---

## Supported Cache Paths (Auto‑detected)

The tool automatically constructs cache‑style relative paths.  
Typical Trackmania subdirectories include:

| Type          | Cache Path                       |
| ------------- | -------------------------------- |
| Images        | `Skins\MediaTracker\Images\`     |
| Sounds        | `Skins\MediaTracker\Sounds\`     |
| Music         | `Skins\ChallengeMusics\`         |
| Mods          | `Skins\Stadium\Mod\`             |
| Advertisement | `Skins\Any\Advertisement\`       |

*(All path components are URL‑encoded to match Trackmania’s internal cache format.)*

---

## Notes

- Multi‑threading uses `ProcessPoolExecutor` with one worker per CPU core
- Skipped extensions: `.txt`, `.loc`
- Duplicate filenames are prevented by the reversed‑MD5 prefix (double‑hash safety)
- The GUI stays responsive thanks to a queue‑based log system
- Temporary zip extraction folders are removed automatically

---

## License

Feel free to use, modify, and distribute.