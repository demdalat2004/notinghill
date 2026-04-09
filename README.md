# NotingHill

**Local File Intelligence System** — Index, search, and understand your files using full-text search, AI-powered natural language queries, timeline browsing, and duplicate detection. Everything runs locally; no data leaves your machine.

```
╔══════════════════════════════════════════╗
║          N O T I N G H I L L            ║
║     Local File Intelligence System      ║
╚══════════════════════════════════════════╝
```

---

## Features

| | Feature | Description |
|---|---|---|
| 🔍 | **Natural language search** | Ask in plain English/Vietnamese — AI generates SQL and queries your index |
| 📄 | **Full-text search** | FTS5-powered search across file names, content, and metadata |
| 🗂️ | **File indexing** | Supports txt, md, pdf, docx, xlsx, jpg/png/HEIC (EXIF), mp3/audio |
| 🕐 | **Timeline** | Browse your files by year → month → day |
| 🔁 | **Duplicate detection** | Exact (SHA-256) + similar text (SimHash) + similar images (pHash) |
| 🤖 | **LLM integration** | Works with Ollama (local), OpenAI-compatible APIs, LM Studio |
| 📊 | **Dashboard** | Live stats, active jobs, recent files |
| 🖼️ | **Image browser** | Gallery view with EXIF data, GPS, camera model |
| ⚡ | **Fast** | LSH-based dedup (O(n log n) vs O(n²)), optional Rust extension |
| 🔒 | **Local first** | SQLite database, port 7878, no telemetry |

---

## Requirements

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |
| PowerShell | 5+ (Windows) |

---

## Quick Start

### 1. Clone

```powershell
git clone https://github.com/demdalat2004/notinghill.git
cd notinghill
```

### 2. Allow PowerShell scripts (one-time)

```powershell
Unblock-File .\run_app.ps1
Unblock-File .\run_dev.ps1
```

### 3. Run (production)

```powershell
.\run_app.ps1
```

The script will automatically:
- Create a Python virtual environment (`.venv`)
- Install Python dependencies
- Build the Rust extension if Rust is installed (optional)
- Build the React frontend
- Start the app at **http://127.0.0.1:7878**

### 4. Run (development — hot reload)

```powershell
.\run_dev.ps1
```

- Backend: http://127.0.0.1:7878
- Frontend (Vite): http://127.0.0.1:5173

---

## First Use

1. Open **http://127.0.0.1:7878**
2. Go to **Indexing** → click **Add Folder** → pick a folder (e.g. `C:\Users\you\Documents`)
3. Indexing runs in the background — watch progress in real-time
4. Go to **Search** → ask anything

---

## AI / LLM Setup

NotingHill supports three search modes:

| Mode | Description |
|---|---|
| `nl2sql` | **Recommended.** Natural language → SQL → execute → answer |
| `fts_plus_llm` | FTS keyword search + LLM narration |
| `fts_only` | No LLM. Pure FTS keyword search |

### Using Ollama (free, runs locally)

```powershell
# 1. Install Ollama from https://ollama.com
# 2. Pull a model
ollama pull gemma3:4b
```

Then in NotingHill → **Settings → LLM**:

| Setting | Value |
|---|---|
| Provider | `ollama` |
| URL | `http://127.0.0.1:11434` |
| Model | `gemma3:4b` |
| Search Mode | `nl2sql` |
| Enable LLM | ✓ |

### Example queries (nl2sql mode)

```
images related to Phong
files modified this week
10 largest PDF files
documents containing "invoice"
photos taken with Canon camera
duplicates wasting the most space
videos longer than 10 minutes
how many files were indexed today?
what's in the 2026 folder?
```

---

## Optional: Rust Extension

Accelerates pHash, SimHash, and SHA-256 batch processing. The app runs without it.

| Operation | Pure Python | With Rust |
|---|---|---|
| pHash per image | ~340 ms | ~7 ms (**~50×**) |
| SimHash per file | ~2 ms | ~0.08 ms (**~25×**) |
| Dedup 500K files | ~34 hours | ~3 min (**LSH**) |

```powershell
# Install Rust from https://rustup.rs, then:
.\venv\Scripts\activate
cd rust_ext
pip install maturin
maturin develop --release
```

`run_app.ps1` builds the extension automatically if Rust is installed.
See [`rust_ext/BUILD.md`](rust_ext/BUILD.md) for troubleshooting.

---

## Project Structure

```
notinghill/
├── backend/
│   ├── main.py                        ← FastAPI entry point
│   ├── config.py                      ← Port, paths, worker count
│   ├── requirements.txt
│   ├── profiling/                     ← Benchmark scripts
│   │   ├── profile_pipeline.py
│   │   └── profile_dedup.py
│   └── app/
│       ├── api/                       ← REST route handlers
│       ├── core/                      ← file_classifier, job_queue, time_utils
│       ├── db/                        ← schema.sql, connection, repos
│       └── services/
│           ├── indexing_service.py    ← scan → extract → hash → persist
│           ├── dedup_service.py       ← exact + LSH near-dedup
│           ├── search_service.py      ← routes nl2sql / fts_plus_llm / fts_only
│           ├── nl2sql_service.py      ← NL → SQL → execute → narrate
│           ├── llm_service.py         ← Ollama / OpenAI abstraction
│           ├── lsh/lsh_index.py       ← banding LSH (no external deps)
│           ├── extractors/            ← pdf, docx, xlsx, image, mp3, text
│           └── signatures/            ← sha256, simhash, phash (Rust-accelerated)
│
├── frontend/
│   └── src/
│       ├── pages/                     ← Dashboard, Search, Timeline, Duplicates,
│       │                                 Images, Multimedia, Indexing, Settings
│       ├── i18n/translations.ts       ← English + Vietnamese
│       └── store/index.ts             ← Zustand global state
│
├── rust_ext/                          ← Optional PyO3 Rust extension
│   ├── src/lib.rs
│   ├── Cargo.toml
│   └── BUILD.md
│
├── run_app.ps1                        ← Production launcher
├── run_dev.ps1                        ← Dev launcher (hot reload)
├── build_exe.ps1                      ← PyInstaller standalone exe
└── PERFORMANCE.md                     ← Optimization guide
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard` | Stats, active jobs, recent files |
| GET | `/api/search?q=` | FTS keyword search |
| POST | `/api/search/ask` | Natural language query (LLM) |
| GET | `/api/search/item/{id}` | File detail + extracted content |
| POST | `/api/search/open/{id}` | Open file in OS default app |
| POST | `/api/search/reveal/{id}` | Reveal in Explorer/Finder |
| GET | `/api/timeline/buckets` | Timeline bucket counts |
| GET | `/api/images` | Image browser with filters |
| GET | `/api/duplicates/exact` | Exact duplicate groups |
| GET | `/api/duplicates/similar-text` | Near-duplicate documents |
| GET | `/api/duplicates/similar-images` | Near-duplicate images |
| POST | `/api/index/roots` | Add folder + start indexing |
| GET | `/api/index/jobs` | Job history + live progress |
| GET | `/api/settings/llm` | LLM configuration |
| POST | `/api/settings/llm` | Update LLM settings |
| POST | `/api/settings/llm/test` | Test LLM connection |
| GET | `/api/docs` | Swagger UI |

---

## Database

| OS | Location |
|---|---|
| Windows | `%APPDATA%\NotingHill\app.db` |
| macOS / Linux | `~/.notinghill/app.db` |

Key tables: `items`, `item_content`, `item_metadata`, `fts_items` (FTS5 virtual table), `duplicate_groups`, `roots`, `index_jobs`.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `NH_PORT` | `7878` | HTTP port |
| `NH_HOST` | `127.0.0.1` | Bind address |
| `NH_WORKERS` | `4` | Indexing thread pool size |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | SQLite (WAL mode, FTS5, 128 MB cache) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Zustand |
| Extractors | pdfplumber, python-docx, openpyxl, Pillow, mutagen |
| AI / LLM | Ollama, OpenAI-compatible APIs, LM Studio |
| Performance (optional) | Rust + PyO3, rayon |

---

## Performance

For 500K+ files see [`PERFORMANCE.md`](PERFORMANCE.md). Run the profiler:

```powershell
cd backend
python -m profiling.profile_pipeline
python -m profiling.profile_dedup
```

---

## License

MIT
