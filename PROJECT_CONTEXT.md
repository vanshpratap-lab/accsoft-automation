PROJECT_CONTEXT.md



# PROJECT: Accsoft Automation

---

## CURRENT STATUS

Project has successfully completed Phase 3.4 (Assignment Extraction).

Automation pipeline is now able to:

* Login to Accsoft portal
* Detect subjects with new assignments
* Navigate into each subject
* Extract assignment metadata
* Download assignment files
* Extract readable content from files (PDF, DOCX, Images via OCR)

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

## NEXT PHASE

### Phase 3.5: AI-Based Assignment Solving

Goal:

* Take extracted questions
* Send to AI model
* Generate answers
* Prepare for upload

---

## FINAL GOAL

Fully automated pipeline:

Login → Detect → Open → Extract → Download → Read → Solve → Upload

---

## NOTES FOR NEXT SESSION

* System is stable and functional
* Focus next on:

  * AI integration
  * Answer generation
  * Output formatting for submission

---
