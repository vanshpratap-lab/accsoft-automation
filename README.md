# Accsoft Automation

Automates the Accsoft student portal pipeline:

Login → Detect assignments → Open subject → Extract → Download → Read (PDF/DOCX/OCR) → Solve (AI) → Upload.

See `PROJECT_CONTEXT.md` for phase-by-phase status.

---

## 1. Python dependencies (pip)

```bash
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
```

Playwright also needs its browser binary (one-time):

```bash
playwright install chromium
```

## 2. System dependencies (NOT pip-installable)

These external tools must be installed at the OS level, otherwise the OCR /
handwriting steps fail at runtime.

| Tool | Needed by | Windows | Linux (Debian/Ubuntu) |
|------|-----------|---------|------------------------|
| **Tesseract-OCR** | `pytesseract` (OCR) | Install the UB-Mannheim build, then confirm `tesseract --version` | `sudo apt-get install tesseract-ocr` |
| **Poppler** (`pdftoppm`) | `pdf2image` (scanned PDFs) | Add Poppler `bin/` to `PATH` | `sudo apt-get install poppler-utils` |
| **Node.js** | handwritten answer PDF (Phase 3.5b) | nodejs.org installer | `sudo apt-get install nodejs` |

### Handwriting add-on (optional)

Phase 3.5b rasterizes answers into handwriting via the `text-to-handwriting`
project's `generate.js`. Clone/build it and point the app at the script through
`HANDWRITING_SCRIPT` (see below). If it is missing, the app automatically falls
back to a plain PDF.

## 3. Environment variables (`.env`)

Create a `.env` file in the project root (it is git-ignored):

```dotenv
OPENROUTER_API_KEY=your_key_here          # required for AI answer generation
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe   # optional override
HANDWRITING_SCRIPT=C:\path\to\text-to-handwriting\generate.js # optional override
```

`TESSERACT_CMD` and `HANDWRITING_SCRIPT` are optional: the app auto-detects the
common Windows Tesseract path and falls back to `tesseract` on `PATH`.

## 4. Run

```bash
python main.py
```

Downloads are written to `downloads/` and generated answers to `answers/`
(both git-ignored).
