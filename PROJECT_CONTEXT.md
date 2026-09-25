PROJECT_CONTEXT.md



# PROJECT: Accsoft Automation

---

## CURRENT STATUS

Project has an end-to-end implementation through answer upload. The current
Ubuntu configuration uses the standard PDF output path; handwritten PDF output
is intentionally deferred until its replacement API/integration is available.

Automation pipeline is now able to:

* Login to Accsoft portal
* Detect subjects with new assignments
* Navigate into each subject
* Extract assignment metadata
* Download assignment files
* Extract readable content from files (PDF, DOCX, Images via OCR)
* Generate AI answers through OpenRouter
* Create a standard answer PDF and upload it to the portal

---

## COMPLETED PHASES

### Phase 1: Login + Navigation ✅

* Open login page
* Enter credentials
* Submit form
* Detect successful login via URL
* Navigate: Dashboard → Academic → Assignments

---

### Phase 2: Assignment Detection ✅

* Locate assignments table
* Filter valid rows
* Detect subjects with new assignments
* Store subjects in structured format

---

### Phase 3.1: Subject Navigation ✅

* Open only subjects with new assignments
* Use row index strategy (avoid stale locators)
* Stable navigation flow:
  Assignments → Subject → Assignments

---

### Phase 3.2: Assignment Extraction ✅

* Navigate to Assignment.aspx page
* Extract:

  * Assignment Number
  * Due Date
  * Download availability
* Handle dynamic table structure

---

### Phase 3.3: File Downloading ✅

* Detect download links
* Use Playwright download API
* Save files locally
* Organized folder structure:

downloads/<subject_name>/<filename>

---

### Phase 3.4: File Reading + OCR ✅

#### Supported formats:

* PDF → using pdfplumber
* DOCX → using python-docx
* Images → using pytesseract (OCR)
* Scanned PDFs → OCR fallback via pdf2image + Tesseract

#### Features:

* Automatic fallback if PDF has no text
* OCR integration working (Tesseract configured manually)
* Poppler installed for PDF → image conversion

#### Processing:

* Extract raw text
* Clean text (remove empty lines)
* Detect questions using regex
* Output structured questions

#### Current limitations:

* Some math equations not perfectly extracted
* Occasional missing question (rare edge case)
* OCR output may contain noise

---

## CURRENT OUTPUT FORMAT

For each subject:

* Assignment metadata printed
* File downloaded
* Questions extracted and printed

Example:

=== Assignment 06 ===
Questions:
Q1 ...
Q2 ...
Q3 ...

---

## PROJECT STRUCTURE

* main.py → core automation logic
* PROJECT_CONTEXT.md → project state
* requirements.txt → dependencies
* downloads/ → saved assignment files (ignored in git)

The Linux MVP now also supports `setup`, `run`, `test`, `status`, `enable`, and
`disable` command modes. Credentials are stored through the OS keyring when configured,
and the daily schedule is stored under the user's XDG configuration directory. Ubuntu
user-level systemd unit generation is implemented; the timer is enabled only when the
customer explicitly runs the `enable` command.

---

## TECH STACK

* Python 3.14
* Playwright (sync API)
* pdfplumber
* python-docx
* pytesseract (OCR)
* pdf2image + Poppler

---

## GIT WORKFLOW

* main → stable branch
* dev → active development branch

---

## IMPORTANT RULES

* Do NOT modify Phase 1, 2, 3.1 logic
* Extend only newer phases
* Keep navigation stable (no page.go_back)
* Always use re-fetch strategy for DOM

---

## CURRENT WORK

### Reliability fixes

* Download assignment files through the logged-in browser session and reject
  portal HTML/error pages before extraction.
* Re-find each subject by name after navigation so changing assignment counts
  do not cause the next subject to open by a stale row index.
* Return to the saved subject URL after upload instead of relying on browser
  history.
* Confirm that a submitted assignment changes to `Re-Upload` before reporting
  upload success.
* Skip PDF creation and upload when no usable questions are extracted from an
  assignment file.
* Keep browser automation visible during runs.
* Use standard PDF output until handwritten PDF generation is reintroduced.

---

## FINAL GOAL

Fully automated pipeline:

Login → Detect → Open → Extract → Download → Read → Solve → Upload

---

## NOTES FOR NEXT SESSION

* System is stable and functional
* Focus next on validating the scheduled Linux run and adding reliable local logs.

---
