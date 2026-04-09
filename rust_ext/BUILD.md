# Building the Rust Extension (`notinghill_ext`)

The Rust extension accelerates three bottlenecks identified by profiling:

| Function            | Pure Python | Rust      | Speedup |
|---------------------|-------------|-----------|---------|
| `phash_image_data`  | ~40 ms/img  | ~0.8 ms   | ~50×    |
| `simhash64`         | ~8 ms/file  | ~0.3 ms   | ~25×    |
| `sha256_batch`      | sequential  | parallel  | ~4–15×  |
| `hamming_batch`     | O(n) Python | O(n) SIMD | ~20×    |

All Python services fall back automatically if the extension is absent.
**The app works without Rust — building is optional but recommended for 500K+ files.**

---

## Prerequisites

### 1. Install Rust (Windows)
```powershell
# Download and run rustup installer
Invoke-WebRequest https://win.rustup.rs -OutFile rustup-init.exe
.\rustup-init.exe -y
# Restart terminal after installation
```

### 2. Install maturin
```powershell
# Inside your Python venv (same one used to run NotingHill)
pip install maturin
```

---

## Build & Install

### Development install (editable, fastest iteration)
```powershell
cd notinghill\rust_ext
maturin develop --release
```
This compiles and installs the `.pyd` file directly into your active venv.

### Build a wheel (for distribution / PyInstaller packaging)
```powershell
cd notinghill\rust_ext
maturin build --release
# Wheel appears in: rust_ext\target\wheels\notinghill_ext-*.whl
pip install target\wheels\notinghill_ext-0.1.0-*.whl
```

---

## Verify installation

```python
import notinghill_ext
# SHA-256 a file
print(notinghill_ext.sha256_file("C:/some/file.pdf"))

# pHash (needs Pillow to prepare pixels)
from PIL import Image
with Image.open("photo.jpg") as img:
    px = bytes(img.convert("L").resize((32,32)).getdata())
print(notinghill_ext.phash_image_data(px, 32))

# SimHash
print(notinghill_ext.simhash64("the quick brown fox jumps over the lazy dog " * 10))
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `linker 'link.exe' not found` | Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with "C++ build tools" workload |
| `error[E0463]: can't find crate for std` | Run `rustup target add x86_64-pc-windows-msvc` |
| `ImportError: DLL load failed` | Make sure you're using the same Python (bitness, version) that maturin built against |
| Extension not found at runtime | The `.pyd` file must be in `backend/` or on `sys.path`. `maturin develop` handles this automatically. |

---

## How the fallback works

Each Python service checks for the extension at import time:

```python
try:
    import notinghill_ext as _ext
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False
```

If `_HAS_RUST` is `False`, the pure-Python implementation is used transparently.
No configuration needed — build the extension to enable acceleration.
