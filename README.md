# Cache Hash Generator

A small Tkinter-based utility for generating **Trackmania cache-style filenames** using **reversed MD5 hashes**.  
It supports exporting files individually or packing them into a hashed ZIP archive.

---

## Features

- Generates **reversed-byte MD5 hashes** (uppercase hex)
- Builds Trackmania-compatible cache paths automatically
- Supports:
  - **Single-file output**
  - **ZIP-packed output** (ZIP itself is also hashed)
- URL-encodes filenames with non-ASCII characters
- Remembers the last output directory
- Simple GUI built with `tkinter`

---

## Supported Cache Paths

| Type | Cache Path |
|------|------------|
| Images | `Skins\MediaTracker\Images\` |
| Sounds | `Skins\MediaTracker\Sounds\` |
| Music | `Skins\ChallengeMusics\` |
| Mods | `Skins\Stadium\Mod\` |
| Advertisement | `Skins\Any\Advertisement\` |

*(Paths are URL-encoded internally to match Trackmania cache format.)*

---

## How It Works

### Hashing

- Each file is hashed using **MD5**
- The MD5 hash bytes are **reversed**
- The result is converted back to uppercase hexadecimal

**Example output filename:**
<REVERSED_MD5>_Skins%5cMediaTracker%5cImages%5cmyimage.png


---

### ZIP Mode

- Each file inside the ZIP uses its **own reversed MD5 filename**
- The ZIP archive itself is hashed after creation
- The ZIP filename is generated from the hash of its contents

**Example ZIP filename:**
<ZIP_REVERSED_MD5>_Skins%5cStadium%5cMod%5cMyPack.zip


---

## Usage

### Requirements

- Python 3.8 or newer
- No external dependencies (standard library only)

### Run

```bash
python cache_hash_generator.py