# NotingHill

**Local File Intelligence System** — Index, search, and organize your files with full-text search, timeline, and duplicate detection.

```
╔══════════════════════════════════════════╗
║          N O T I N G H I L L            ║
║     Local File Intelligence System      ║
╚══════════════════════════════════════════╝
```

---

## Features

| Feature                 | Description                                                      |
| ----------------------- | ---------------------------------------------------------------- |
| **Full-text search**    | SQLite FTS5 — search file names, content, metadata               |
| **File indexing**       | txt, md, pdf, docx, xlsx, images (EXIF), mp3/audio               |
| **Timeline**            | Browse files by year / month / day                               |
| **Duplicate detection** | Exact (sha256) + similar text (simhash) + similar images (phash) |
| **Live progress**       | Real-time job monitoring per folder                              |
| **Futurist UI**         | Dark/light theme, EN/VI bilingual                                |
| **Local first**         | All data stays on your machine (SQLite, port 7878)               |
| **Portable**            | PyInstaller exe — no Python install needed                       |

---

## Requirements

| Tool       | Min version                       |
| ---------- | --------------------------------- |
| Python     | 3.11+                             |
| Node.js    | 18+                               |
| npm        | 9+                                |
| PowerShell | 5+ (Windows) / pwsh (macOS/Linux) |

---

## Quick Start

### Development (hot reload)

#### Windows

```powershell
.\run_dev.ps1
```

#### macOS/Linux

install build tool for python:

```bash
 sudo apt-get update; sudo apt-get install -y \
 build-essential \
 libssl-dev \
 zlib1g-dev \
 libbz2-dev \
 libreadline-dev \
 libsqlite3-dev \
 wget \
 curl \
 llvm \
 libncursesw5-dev \
 xz-utils \
 tk-dev \
 libxml2-dev \
 libxmlsec1-dev \
 libffi-dev \
 liblzma-dev
```

install python via penv:

```bash
   pyenv install 3.13.12 --force
```

```bash
./run_dev.sh
```

This will:

1. Create `.venv` if it doesn't exist
2. `pip install` all Python dependencies
3. `npm install` frontend packages
4. Start backend on `http://127.0.0.1:7878`
5. Start Vite dev server on `http://127.0.0.1:5173`

Open `http://127.0.0.1:5173` in your browser.

---

### Production (built frontend)

```powershell
.\run_app.ps1
```

This will:

1. Build the React frontend → `backend/static/`
2. Start FastAPI serving both API and static files on port 7878

Open `http://127.0.0.1:7878`.

---

### Build standalone EXE

```powershell
.\build_exe.ps1
```

This will:

1. Install all dependencies into `.venv`
2. Build the React frontend
3. Run PyInstaller
4. Output: `backend/dist/NotingHill/notinghill.exe` + `NotingHill-windows-x64.zip`

**Windows:** Double-click `notinghill.exe` — browser opens automatically.
**macOS:** Open `backend/dist/NotingHill.app`.

---

## Project Structure

```
notinghill/
├── backend/
│   ├── main.py                  ← FastAPI entry point
│   ├── config.py                ← Port, paths, settings
│   ├── requirements.txt
│   ├── app/
│   │   ├── api/                 ← 6 route files
│   │   │   ├── routes_dashboard.py
│   │   │   ├── routes_search.py
│   │   │   ├── routes_timeline.py
│   │   │   ├── routes_duplicates.py
│   │   │   ├── routes_indexing.py
│   │   │   └── routes_settings.py
│   │   ├── core/
│   │   │   ├── file_classifier.py
│   │   │   ├── job_queue.py
│   │   │   └── time_utils.py
│   │   ├── db/
│   │   │   ├── schema.sql       ← 13 tables + FTS5
│   │   │   ├── connection.py
│   │   │   ├── repo_items.py
│   │   │   ├── repo_content.py
│   │   │   ├── repo_search.py   ← FTS5 queries
│   │   │   ├── repo_duplicates.py
│   │   │   ├── repo_timeline.py
│   │   │   └── repo_jobs.py     ← jobs + roots + settings
│   │   └── services/
│   │       ├── indexing_service.py   ← main pipeline
│   │       ├── dedup_service.py      ← sha256 + simhash + phash
│   │       ├── search_service.py
│   │       ├── extractors/
│   │       │   ├── text_extractor.py
│   │       │   ├── pdf_extractor.py
│   │       │   ├── docx_extractor.py
│   │       │   ├── xlsx_extractor.py
│   │       │   ├── image_extractor.py
│   │       │   └── mp3_extractor.py
│   │       └── signatures/
│   │           ├── sha256_service.py
│   │           ├── simhash_service.py
│   │           └── phash_service.py
│   └── build/
│       └── notinghill.spec      ← PyInstaller spec
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── index.css            ← Futurist design system
│   │   ├── i18n/
│   │   │   └── translations.ts  ← EN + VI
│   │   ├── store/
│   │   │   └── index.ts         ← Zustand global state
│   │   ├── api/
│   │   │   └── client.ts        ← Axios API layer
│   │   ├── utils/
│   │   │   └── helpers.ts
│   │   ├── components/
│   │   │   ├── layout/Layout.tsx
│   │   │   └── ui/index.tsx     ← StatCard, FileRow, Badge...
│   │   └── pages/
│   │       ├── Dashboard.tsx
│   │       ├── Search.tsx
│   │       ├── Timeline.tsx
│   │       ├── Duplicates.tsx
│   │       ├── Indexing.tsx
│   │       └── Settings.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── run_dev.ps1                  ← Dev mode
├── run_app.ps1                  ← Production mode
└── build_exe.ps1                ← Build standalone exe
```

---

## API Endpoints

| Method | Path                             | Description                      |
| ------ | -------------------------------- | -------------------------------- |
| GET    | `/api/dashboard`                 | Stats, active jobs, recent files |
| GET    | `/api/search?q=...`              | Full-text search with filters    |
| GET    | `/api/search/item/{id}`          | File detail + preview            |
| POST   | `/api/search/open/{id}`          | Open file in OS                  |
| GET    | `/api/timeline/buckets`          | Bucket counts by zoom level      |
| GET    | `/api/timeline/items/{bucket}`   | Files in bucket                  |
| GET    | `/api/duplicates/exact`          | Exact duplicate groups           |
| GET    | `/api/duplicates/similar-text`   | Near-duplicate documents         |
| GET    | `/api/duplicates/similar-images` | Near-duplicate images            |
| GET    | `/api/index/roots`               | List indexed folders             |
| POST   | `/api/index/roots`               | Add + start indexing folder      |
| POST   | `/api/index/roots/{id}/reindex`  | Reindex a root                   |
| GET    | `/api/index/jobs`                | Job history + active jobs        |
| GET    | `/api/settings`                  | All app settings                 |
| POST   | `/api/settings`                  | Update a setting                 |
| GET    | `/api/docs`                      | Swagger UI                       |

---

## Database

Data is stored in:

- **Windows:** `%APPDATA%\NotingHill\app.db`
- **macOS/Linux:** `~/.notinghill/app.db`

13 tables including `item_fts` (FTS5 virtual table for full-text search).

---

## Notes

- **First run:** Add a folder via the Indexing tab. The app scans in the background using a thread pool (4 workers by default).
- **Incremental indexing:** Only changed files (size + mtime) are re-indexed on subsequent scans.
- **Duplicate detection** runs automatically after each indexing job.
- **OCR:** Disabled by default. Enable in Settings (requires Tesseract installed separately).
- **Port:** Default 7878. Change via `NH_PORT` environment variable or Settings.
