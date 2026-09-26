import argparse
from datetime import datetime
import getpass
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
import requests
import pdfplumber
import pytesseract
from urllib.parse import unquote, urljoin, urlparse
from PIL import Image
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()


KEYRING_SERVICE = "accsoft-automation"
APP_NAME = "accsoft-automation"
CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
SCHEDULE_CONFIG_PATH = CONFIG_DIR / "schedule.toml"
STATE_DIR = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state")) / APP_NAME
LOG_PATH = STATE_DIR / "agent.log"
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
SYSTEMD_SERVICE_NAME = f"{APP_NAME}.service"
SYSTEMD_TIMER_NAME = f"{APP_NAME}.timer"
LOGGER = logging.getLogger(APP_NAME)


def _configure_logging() -> None:
    """Configure a private local log without recording secrets or portal responses."""
    if not LOGGER.handlers:
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
            os.chmod(LOG_PATH, 0o600)
        except OSError as error:
            handler = logging.StreamHandler()
            print(f"  [LOG WARN] Local log unavailable; using console logging: {error}")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOGGER.addHandler(handler)
        LOGGER.setLevel(logging.INFO)


def _read_keyring_secret(name: str) -> str:
    """Read a secret from the OS keyring when the optional dependency is available."""
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, name) or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# CONFIGURATION — environment overrides preserve the current defaults
# ---------------------------------------------------------------------------
LOGIN_URL = "https://accsoft.piemr.edu.in/accsoft_piemr/StudentLogin.aspx"
USERNAME = os.getenv("ACCSOFT_USERNAME") or _read_keyring_secret("username") or "51110106439"
PASSWORD = os.getenv("ACCSOFT_PASSWORD") or _read_keyring_secret("password") or "51110106439"

DOWNLOADS_DIR = "downloads"
ANSWERS_DIR = "answers"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"
OPENROUTER_TIMEOUT_SECONDS = 30
AI_REQUEST_DELAY_SECONDS = 2

BROWSER_HEADLESS = False
BROWSER_CLOSE_DELAY_MS = 5000
DEFAULT_SCHEDULE_TIME = "18:00"

PDF_TEXT_MINIMUM_LENGTH = 200
QUESTION_MINIMUM_LENGTH = 8

LOGIN_TIMEOUT_MS = 120000
PAGE_LOAD_TIMEOUT_MS = 60000
CONTENT_TIMEOUT_MS = 15000
SHORT_NAV_TIMEOUT_MS = 30000
AJAX_WAIT_MS = 2000
RETRY_WAIT_MS = 3000
UPLOAD_INPUT_TIMEOUT_MS = 10000
NEW_ASSIGNMENT_DETACH_TIMEOUT_MS = 10000
MENU_EXPAND_WAIT_MS = 1500
POST_NAV_WAIT_MS = 2000
RETURN_WAIT_MS = 1000
HANDWRITING_PROCESS_TIMEOUT_SECONDS = 60
ASSIGNMENTS_CONTAINER_SELECTOR = "#ctl00_ContentPlaceHolder1_DataList2"
ASSIGNMENT_ROW_SELECTOR = "tr.GreenPage2"


def _validate_configuration() -> None:
    """Validate startup configuration without changing the portal workflow."""
    required_text = {
        "LOGIN_URL": LOGIN_URL,
        "USERNAME": USERNAME,
        "PASSWORD": PASSWORD,
        "USERNAME_SELECTOR": USERNAME_SELECTOR,
        "PASSWORD_SELECTOR": PASSWORD_SELECTOR,
        "LOGIN_BTN_SELECTOR": LOGIN_BTN_SELECTOR,
    }
    missing = [name for name, value in required_text.items() if not str(value).strip()]
    if missing:
        raise RuntimeError(f"Missing configuration value(s): {', '.join(missing)}")

    positive_values = {
        "OPENROUTER_TIMEOUT_SECONDS": OPENROUTER_TIMEOUT_SECONDS,
        "PDF_TEXT_MINIMUM_LENGTH": PDF_TEXT_MINIMUM_LENGTH,
        "QUESTION_MINIMUM_LENGTH": QUESTION_MINIMUM_LENGTH,
        "LOGIN_TIMEOUT_MS": LOGIN_TIMEOUT_MS,
        "PAGE_LOAD_TIMEOUT_MS": PAGE_LOAD_TIMEOUT_MS,
        "CONTENT_TIMEOUT_MS": CONTENT_TIMEOUT_MS,
    }
    invalid = [name for name, value in positive_values.items() if value <= 0]
    if invalid:
        raise RuntimeError(f"Configuration values must be positive: {', '.join(invalid)}")

    if not _OR_API_KEY:
        print("  [CONFIG WARN] OPENROUTER_API_KEY is missing; AI generation will be skipped")

# ---------------------------------------------------------------------------
# EXTERNAL TOOL PATHS — override via .env, with sensible defaults
# ---------------------------------------------------------------------------
def _configure_tesseract() -> None:
    """Point pytesseract at the Tesseract binary.

    Priority: TESSERACT_CMD from .env -> common Windows default -> system PATH.
    """
    for candidate in (
        os.getenv("TESSERACT_CMD", ""),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    ):
        if candidate and os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


_configure_tesseract()


# ---------------------------------------------------------------------------
# SELECTORS — inspect the portal (F12 → Elements) and replace each value
# ---------------------------------------------------------------------------
USERNAME_SELECTOR   = "#ctl00_cph1_txtStuUser"
PASSWORD_SELECTOR   = "#ctl00_cph1_txtStuPsw"
LOGIN_BTN_SELECTOR  = "#btnStuLogin"


# ---------------------------------------------------------------------------
# PHASE 3.4: File reading + OCR fallback
# ---------------------------------------------------------------------------
def extract_pdf_text(path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"  [PDF ERROR] {e}")
    return text


def extract_pdf_with_ocr(path: str) -> str:
    try:
        import pdf2image
        images = pdf2image.convert_from_path(path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        print("  [OCR USED - PDF]")
        return text
    except Exception as e:
        print(f"  [PDF OCR ERROR] {e}")
        return ""


def extract_image_text(path: str) -> str:
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        print("  [OCR USED - IMAGE]")
        return text
    except Exception as e:
        print(f"  [OCR ERROR] {e}")
        return ""


def extract_docx_text(path: str) -> str:
    """Extract text (paragraphs + table cells) from a .docx file."""
    try:
        import docx
    except ImportError:
        print("  [DOCX ERROR] python-docx is not installed — run: pip install python-docx")
        return ""
    try:
        document = docx.Document(path)
        parts = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells)
        return "\n".join(parts)
    except Exception as e:
        print(f"  [DOCX ERROR] {e}")
        return ""


def read_file_content(filepath: str) -> str:
    """Extract text from PDF, DOCX, or image. OCR fallback for image-based PDFs."""
    try:
        ext = filepath.lower()

        if ext.endswith(".pdf"):
            text = extract_pdf_text(filepath)
            if not text or len(text.strip()) < PDF_TEXT_MINIMUM_LENGTH:
                print("  [WARN] PDF text too short — trying OCR fallback...")
                text = extract_pdf_with_ocr(filepath)
            if not text.strip():
                print("  [WARN] No readable content extracted from PDF")
            return clean_text(text)

        if ext.endswith((".jpg", ".jpeg", ".png")):
            return extract_image_text(filepath)

        if ext.endswith(".docx"):
            return clean_text(extract_docx_text(filepath))

        if ext.endswith(".doc"):
            print("  [warn] Legacy .doc not supported — convert to .docx first")
            return ""

        return ""
    except Exception as e:
        print(f"  [warn] Could not read {filepath}: {e}")
        return ""


def clean_text(text: str) -> str:
    """Strip empty lines only — no merging, to preserve equations and structure."""
    return "\n".join(line.strip() for line in text.split("\n") if line.strip())


def extract_questions(text: str) -> list[str]:
    """Split text into questions using numbered-prefix pattern."""
    import re
    text = text.replace("\r", "\n")
    pattern = r'(?:Q\.?\s*\d+|\n\d{1,2}[).])'
    parts = re.split(pattern, text)

    questions = []
    for part in parts[1:]:  # parts[0] is preamble before first question
        part = part.strip()
        if part:
            questions.append(part)

    return questions


# ---------------------------------------------------------------------------
# PHASE 3.3: Authenticated assignment-file download
# ---------------------------------------------------------------------------
def download_assignment_file(page, relative_url: str) -> str:
    """Download an assignment through the logged-in Playwright context.

    A standalone requests.get call has no portal session cookies, so the portal
    can return its login/error HTML instead of the attachment. Browser-context
    requests share the authenticated session with the visible browser.
    """
    full_url = urljoin(page.url, relative_url)
    filename = unquote(os.path.basename(urlparse(full_url).path)) or "assignment_file"
    filepath = os.path.join(DOWNLOADS_DIR, filename)

    response = page.context.request.get(full_url, timeout=PAGE_LOAD_TIMEOUT_MS)
    if not response.ok:
        raise RuntimeError(f"Server returned HTTP {response.status}")

    body = response.body()
    content_type = response.headers.get("content-type", "").lower()
    looks_like_html = (
        "text/html" in content_type
        or body.lstrip().lower().startswith((b"<!doctype html", b"<html"))
    )
    if not body or looks_like_html:
        raise RuntimeError("Portal returned an HTML/login page instead of the assignment file")

    with open(filepath, "wb") as f:
        f.write(body)
    print(f"  Downloaded: {filepath}")
    return filepath


# ---------------------------------------------------------------------------
# PHASE 3.5: AI Answer Generation (OpenRouter)
# ---------------------------------------------------------------------------
_OR_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def generate_answer(question: str) -> str:
    if not _OR_API_KEY:
        print("  [AI ERROR] OPENROUTER_API_KEY is missing from .env — skipping answer generation")
        return "Error generating answer"
    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {_OR_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://accsoft.piemr.edu.in",
                "X-Title": "Accsoft Automation",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": question}],
            },
            timeout=OPENROUTER_TIMEOUT_SECONDS,
        )
        data = response.json()
        if "error" in data:
            print(f"  [AI API ERROR] {data['error'].get('message', data['error'])}")
            return "Error generating answer"
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [AI ERROR] {e}")
        return "Error generating answer"


# ---------------------------------------------------------------------------
# PHASE 3.5b: Convert .txt answer file to PDF for upload
# ---------------------------------------------------------------------------
def convert_txt_to_pdf(txt_path: str) -> str:
    pdf_path = txt_path.replace(".txt", ".pdf")
    try:
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        content = []
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()
                if line:
                    content.append(Paragraph(line, styles["Normal"]))
                else:
                    content.append(Spacer(1, 8))
        doc.build(content)
        if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) == 0:
            raise RuntimeError("PDF file was not created or is empty")
        print(f"  [3.5b] PDF created: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"  [3.5b] PDF conversion failed: {e}")
        return ""


_HW_SCRIPT = os.getenv(
    "HANDWRITING_SCRIPT",
    r"C:\Users\Hp\Desktop\text-to-handwriting\generate.js",
)


def generate_handwritten_pdf(txt_path: str) -> str:
    pdf_path = txt_path.replace(".txt", ".pdf")
    png_path = txt_path.replace(".txt", ".png")
    try:
        result = subprocess.run(
            ["node", _HW_SCRIPT, txt_path, png_path],
            capture_output=True, text=True, timeout=HANDWRITING_PROCESS_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

        img = Image.open(png_path).convert("RGB")
        img.save(pdf_path, "PDF", resolution=150)
        print(f"  [3.5b] Handwritten PDF created: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"  [3.5b] Handwritten generation failed: {e} — using plain PDF fallback")
        return convert_txt_to_pdf(txt_path)


# ---------------------------------------------------------------------------
# PHASE 3.6: Upload generated answer file to portal
# ---------------------------------------------------------------------------
def upload_assignment(page, file_path: str, assignment_no: str) -> None:
    try:
        print(f"  [3.6] Uploading: {file_path}")
        subject_url = page.url
        page.locator("a:has-text('Upload'):visible").first.click()

        page.wait_for_selector("input[type='file']", timeout=UPLOAD_INPUT_TIMEOUT_MS)
        page.set_input_files("input[type='file']", file_path)
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle")

        # Return to the known subject URL instead of relying on browser history.
        page.goto(subject_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
        page.wait_for_selector(ASSIGNMENTS_CONTAINER_SELECTOR, timeout=CONTENT_TIMEOUT_MS)

        upload_confirmed = False
        assignment_rows = page.locator(f"{ASSIGNMENTS_CONTAINER_SELECTOR} {ASSIGNMENT_ROW_SELECTOR}")
        for i in range(assignment_rows.count()):
            row = assignment_rows.nth(i)
            cells = row.locator("td")
            if cells.count() < 3 or cells.nth(2).inner_text().strip() != assignment_no:
                continue
            button = row.locator("a:has-text('Upload'), a:has-text('Re-Upload')")
            if button.count() and button.first.inner_text().strip().lower() == "re-upload":
                upload_confirmed = True
            break

        if upload_confirmed:
            print(f"  [3.6] Upload confirmed for assignment {assignment_no}")
        else:
            print(f"  [3.6] WARNING: upload was submitted but not confirmed for assignment {assignment_no}")
    except Exception as e:
        print(f"  [3.6] Upload failed: {e}")


# ---------------------------------------------------------------------------
def login(page) -> None:
    """Open the login page, fill credentials, submit, and confirm login."""
    print("[1/4] Navigating to login page...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_TIMEOUT_MS)

    print("[2/4] Filling credentials...")
    page.wait_for_selector(USERNAME_SELECTOR, state="visible")
    page.fill(USERNAME_SELECTOR, USERNAME)
    page.fill(PASSWORD_SELECTOR, PASSWORD)

    print("[3/4] Submitting login form...")
    page.click(LOGIN_BTN_SELECTOR)

    print("[4/4] Waiting for post-login navigation...")
    try:
        page.wait_for_url("**/ParentDesk1.aspx", wait_until="domcontentloaded", timeout=LOGIN_TIMEOUT_MS)
        print("      Login successful.")
    except PlaywrightTimeoutError:
        print(f"      Login failed. Current URL: {page.url}")
        raise RuntimeError("Login failed — did not reach ParentDesk1.aspx. Check credentials.")


def navigate_to_assignments(page) -> None:
    """Click Academic tab to expand submenu, then click Assignments."""
    print("[5/6] Clicking Academic tab...")
    academic = page.get_by_text("Academic", exact=True)
    academic.wait_for(state="visible", timeout=LOGIN_TIMEOUT_MS)
    academic.click()

    print("      Waiting for submenu to expand...")
    page.wait_for_timeout(MENU_EXPAND_WAIT_MS)

    print("[6/6] Clicking Assignments option...")
    assignments = page.get_by_text("Assignments", exact=True)
    assignments.wait_for(state="visible", timeout=LOGIN_TIMEOUT_MS)
    assignments.click()
    print("      Assignments page loaded successfully.")


def _scan_subject_rows(page) -> list[dict]:
    """
    Phase 2: two-pass subject detection.

    Pass 1 — collect subjects where the count column > 0.
    Pass 2 — navigate into each candidate and confirm at least one assignment
              has a visible 'Upload' anchor (not 'Re-Upload').

    Only subjects with a real pending upload are returned.
    """
    rows = page.locator("table tr")
    row_count = rows.count()

    # Pass 1: fast scan of count column
    candidates: list[dict] = []
    for i in range(row_count):
        cells = rows.nth(i).locator("td")
        if cells.count() != 5:
            continue
        subject_name = cells.nth(1).inner_text().strip()
        new_count_text = cells.nth(2).inner_text().strip()
        if not subject_name:
            continue
        try:
            new_count = int(new_count_text)
        except ValueError:
            new_count = 0
        if new_count > 0 and not any(c["subject"] == subject_name for c in candidates):
            candidates.append({"subject": subject_name, "row_index": i})

    print(f"[DEBUG P2] Candidate subjects (count > 0): {[c['subject'] for c in candidates]}")

    # Pass 2: navigate into each candidate and verify real Upload button exists
    targets: list[dict] = []
    for candidate in candidates:
        subject = candidate["subject"]
        row_index = candidate["row_index"]
        print(f"[DEBUG P2] Verifying: {subject}")

        try:
            rows_fresh = page.locator("table tr")
            row = rows_fresh.nth(row_index)
            view_button = row.locator("td").nth(2).locator("a, button")
            if view_button.count() == 0:
                view_button = row.locator("a, button").first
            view_button.click()
            page.wait_for_load_state("domcontentloaded", timeout=SHORT_NAV_TIMEOUT_MS)
            page.wait_for_timeout(AJAX_WAIT_MS)

            container = page.locator(ASSIGNMENTS_CONTAINER_SELECTOR)
            assign_rows = container.locator(ASSIGNMENT_ROW_SELECTOR)
            if assign_rows.count() == 0:
                page.wait_for_timeout(RETRY_WAIT_MS)
                assign_rows = container.locator(ASSIGNMENT_ROW_SELECTOR)

            subject_has_pending = False
            for j in range(assign_rows.count()):
                upload_link = assign_rows.nth(j).locator("a:has-text('Upload'), a:has-text('Re-Upload')")
                if upload_link.count() > 0:
                    try:
                        button_text = upload_link.first.inner_text().strip().lower()
                    except Exception:
                        button_text = ""
                    print(f"[DEBUG P2] Subject row button text: '{button_text}'")
                    if button_text == "upload":
                        subject_has_pending = True
                        break

            if subject_has_pending:
                print(f"[DEBUG P2] {subject} → CONFIRMED pending Upload")
                targets.append(candidate)
            else:
                print(f"[DEBUG P2] {subject} → no real pending Upload — SKIPPED")

        except Exception as e:
            print(f"[DEBUG P2] Error verifying {subject}: {e}")
        finally:
            _return_to_assignments(page)
            page.wait_for_timeout(RETURN_WAIT_MS)

    return targets


def extract_assignments(page) -> list[dict]:
    """Phase 2: scan and print subjects that have new assignments. Returns targets for Phase 3."""
    print("\n[Phase 2] Waiting for assignments table to load...")
    page.wait_for_timeout(POST_NAV_WAIT_MS)

    targets = _scan_subject_rows(page)

    print("=" * 60)
    if not targets:
        print("No subjects with new assignments found.")
    else:
        for t in targets:
            print(f"Subject: {t['subject']} → has new assignments")
    print("=" * 60)

    return targets


def _return_to_assignments(page) -> None:
    """Re-navigate to the assignments page via the Academic submenu."""
    academic = page.get_by_text("Academic", exact=True)
    academic.wait_for(state="visible", timeout=PAGE_LOAD_TIMEOUT_MS)
    academic.click()

    page.wait_for_timeout(MENU_EXPAND_WAIT_MS)

    assignments = page.locator("a:has-text('Assignments')").first
    assignments.wait_for(state="visible", timeout=PAGE_LOAD_TIMEOUT_MS)
    assignments.click()

    page.wait_for_timeout(POST_NAV_WAIT_MS)


def extract_subject_assignments(page, subject_name: str, dry_run: bool = False) -> None:
    """
    Phase 3.2: Extract assignment details using data-label selectors.
    Does NOT click anything.
    """
    print(f"\n  [Phase 3.2] Extracting assignments for: {subject_name}")

    try:
        page.wait_for_selector(ASSIGNMENTS_CONTAINER_SELECTOR, timeout=CONTENT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        print(f"    [warn] Container {ASSIGNMENTS_CONTAINER_SELECTOR} not found.")

    container = page.locator(ASSIGNMENTS_CONTAINER_SELECTOR)
    rows = container.locator(ASSIGNMENT_ROW_SELECTOR)
    count = rows.count()
    print(f"    [debug] Rows inside correct container: {count}")

    # Retry once if AJAX content hasn't rendered yet
    if count == 0:
        print("    [debug] No rows found — retrying after 3s...")
        page.wait_for_timeout(RETRY_WAIT_MS)
        rows = container.locator(ASSIGNMENT_ROW_SELECTOR)
        count = rows.count()
        print(f"    [debug] Rows after retry: {count}")

    total_assignments = 0
    print(f"\n  Subject: {subject_name}")

    for i in range(count):
        print(f"  [DEBUG] Loop row index: {i}")
        row = rows.nth(i)
        cells = row.locator("td")
        cell_count = cells.count()

        print(f"  [DEBUG] Cell count for row {i}: {cell_count}")
        if cell_count < 5:
            print(f"  [DEBUG] Row {i} skipped — fewer than 5 cells")
            continue

        texts = [cells.nth(j).inner_text().strip() for j in range(cell_count)]

        assign_no = texts[2]
        due_date  = texts[3]

        print(f"  [DEBUG] assign_no='{assign_no}' due_date='{due_date}'")
        if not assign_no or not due_date:
            print(f"  [DEBUG] Row {i} skipped — missing assign_no or due_date")
            continue

        upload_link = row.locator("a:has-text('Upload'), a:has-text('Re-Upload')")
        button_text = ""
        if upload_link.count() > 0:
            try:
                button_text = upload_link.first.inner_text().strip().lower()
            except Exception:
                button_text = ""

        print(f"  [DEBUG] Upload button text: '{button_text}'")

        already_submitted = "re-upload" in button_text
        print(f"  [DEBUG] Already submitted: {already_submitted}")

        if already_submitted:
            print(f"  Skipping already submitted assignment: {assign_no}")
            print("  [DEBUG] Continuing to next row...")
            continue

        total_assignments += 1
        print(f"  Assignment {assign_no} | Due: {due_date} | Button: '{button_text}'")

        if dry_run:
            print(f"  [TEST] Would download and process assignment {assign_no}; no changes made")
            continue

        # Phase 3.3: Download through the authenticated browser session.
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        download_link = row.locator('a[href*="Upload/Assignment"]')
        if download_link.count() == 0:
            print(f"  No download link found for {assign_no}")
        else:
            try:
                relative_url = download_link.first.get_attribute("href")
                if not relative_url:
                    raise RuntimeError("Assignment download link has no URL")
                filepath = download_assignment_file(page, relative_url)

                # Phase 3.4 + 3.5: Extract questions → AI answers → save
                content = read_file_content(filepath)
                if content:
                    questions = extract_questions(content)
                    valid_questions = [q for q in questions if len(q.strip()) >= QUESTION_MINIMUM_LENGTH]
                    if not valid_questions:
                        print(f"  [WARN] No valid questions extracted for {assign_no} — skipping PDF and upload")
                        continue

                    subject_safe = subject_name.replace(" ", "_").replace("&", "and")
                    ans_folder = os.path.join(ANSWERS_DIR, subject_safe)
                    os.makedirs(ans_folder, exist_ok=True)
                    ans_file = f"{ans_folder}/assignment_{assign_no}.txt"

                    print(f"\n  === Assignment {assign_no} ===")
                    with open(ans_file, "a", encoding="utf-8") as f:
                        for q in valid_questions:
                            print(f"\n  Q: {q}")
                            answer = generate_answer(q)
                            print(f"  A: {answer}")
                            f.write(f"Q: {q}\nA: {answer}\n\n")
                            time.sleep(AI_REQUEST_DELAY_SECONDS)
                    print(f"\n  Answers saved → {ans_file}")

                    # Phase 3.5b → 3.6: use the reliable plain-PDF path.
                    # Handwritten output is intentionally deferred for now.
                    pdf_file = convert_txt_to_pdf(ans_file)
                    if pdf_file:
                        upload_assignment(page, os.path.abspath(pdf_file), assign_no)
                    else:
                        print("  [3.6] Upload skipped because answer PDF generation failed")
                else:
                    print(f"  [WARN] No readable assignment content for {assign_no} — skipping PDF and upload")
            except Exception as e:
                print(f"  [warn] Download failed for {assign_no}: {e}")

    if total_assignments == 0:
        print("  No assignments found.")

    print(f"  Total assignments found: {total_assignments}")


def _open_subject_by_name(page, subject_name: str) -> None:
    """Open a subject from a freshly rendered assignments table.

    Assignment counts can change after an upload, which makes a previously
    stored row index unreliable. Matching the visible subject name avoids
    accidentally opening the wrong row on later iterations.
    """
    rows = page.locator("table tr")
    for i in range(rows.count()):
        row = rows.nth(i)
        cells = row.locator("td")
        if cells.count() != 5:
            continue
        if cells.nth(1).inner_text().strip() != subject_name:
            continue

        view_button = row.locator("td").nth(2).locator("a, button")
        if view_button.count() == 0:
            view_button = row.locator("a, button").first
        if view_button.count() == 0:
            raise RuntimeError(f"No view button found for subject: {subject_name}")
        view_button.click()
        return

    raise RuntimeError(f"Subject not found in assignments table: {subject_name}")


def open_subjects(page, targets: list[dict], dry_run: bool = False) -> None:
    """
    Phase 3 Step 3.1: click each subject that has new assignments one at a
    time, then re-navigate back to the assignments page before the next one.
    Receives targets from Phase 2 — no re-scan performed.
    """
    print("\n[Phase 3.1] Opening subjects with new assignments...")

    if not targets:
        print("  No subjects with new assignments — nothing to open.")
        return

    print(f"  Found {len(targets)} subject(s) to open.\n")

    for t in targets:
        subject = t["subject"]

        print(f"  Clicking subject: {subject} ...")
        _open_subject_by_name(page, subject)
        print("  Clicked correct subject view button")

        page.wait_for_load_state("domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)

        # Phase 3.2 context guard: wait for old list to detach, then new content to appear
        try:
            page.wait_for_selector(
                "text=New Assignment",
                state="detached",
                timeout=NEW_ASSIGNMENT_DETACH_TIMEOUT_MS,
            )
        except PlaywrightTimeoutError:
            print("  [debug] 'New Assignment' text did not detach — may be AJAX partial reload.")

        try:
            page.wait_for_selector('td[data-label="Assign. No."]', timeout=CONTENT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            print("  [warn] Assignment rows not found — falling back with 3s wait...")
            page.wait_for_timeout(RETRY_WAIT_MS)

        row_count = page.locator('td[data-label="Assign. No."]').count()
        print(f"  Now on subject page, rows: {row_count}")
        print(f"  [debug] Current URL: {page.url}")

        # Phase 3.2: extract assignments from the subject page
        extract_subject_assignments(page, subject, dry_run=dry_run)

        # Navigate back via menu — never rely on browser history
        print("\n  Returning to assignments page...")
        _return_to_assignments(page)
        print("  Assignments table reloaded.\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Accsoft assignment automation")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("run", "test", "status", "setup", "enable", "enable-test", "disable"),
        default="run",
        help="run, inspect safely, show status, or configure credentials",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def _setup_local_credentials() -> None:
    """Store portal credentials in the user's OS keyring."""
    try:
        import keyring
    except ImportError as e:
        raise RuntimeError(
            "The keyring package is required for setup. Install requirements.txt first."
        ) from e

    schedule_time = _prompt_schedule_time()

    username = input("Accsoft username/student ID: ").strip()
    if not username:
        raise RuntimeError("Username cannot be empty")

    password = getpass.getpass("Accsoft password: ")
    if not password:
        raise RuntimeError("Password cannot be empty")

    keyring.set_password(KEYRING_SERVICE, "username", username)
    keyring.set_password(KEYRING_SERVICE, "password", password)
    _save_schedule_time(schedule_time)
    print("Credentials saved securely in the operating-system keyring.")
    print(f"Daily schedule saved for {schedule_time}.")


def _prompt_schedule_time() -> str:
    current = _load_schedule_time()
    entered = input(f"Daily run time [HH:MM, default {current}]: ").strip() or current
    try:
        datetime.strptime(entered, "%H:%M")
    except ValueError as e:
        raise RuntimeError("Schedule time must use 24-hour HH:MM format, for example 18:00") from e
    return entered


def _load_schedule_time() -> str:
    if not SCHEDULE_CONFIG_PATH.is_file():
        return DEFAULT_SCHEDULE_TIME

    for line in SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("daily_time ="):
            value = line.split("=", 1)[1].strip().strip('"')
            try:
                datetime.strptime(value, "%H:%M")
                return value
            except ValueError:
                break
    return DEFAULT_SCHEDULE_TIME


def _save_schedule_time(schedule_time: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SCHEDULE_CONFIG_PATH.write_text(
        f'daily_time = "{schedule_time}"\n',
        encoding="utf-8",
    )
    os.chmod(SCHEDULE_CONFIG_PATH, 0o600)


def _systemd_unit_contents(schedule_time: str, mode: str = "run") -> tuple[str, str]:
    script_path = Path(__file__).resolve()
    service = f"""[Unit]
Description=Accsoft Automation daily run

[Service]
Type=oneshot
WorkingDirectory={script_path.parent}
ExecStart={sys.executable} {script_path} {mode} --scheduled
"""
    timer = f"""[Unit]
Description=Run Accsoft Automation daily at {schedule_time}

[Timer]
OnCalendar=*-*-* {schedule_time}:00
Persistent=true
Unit={SYSTEMD_SERVICE_NAME}

[Install]
WantedBy=timers.target
"""
    return service, timer


def _run_systemctl(*arguments: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


def _enable_schedule(dry_run: bool = False) -> None:
    schedule_time = _load_schedule_time()
    mode = "test" if dry_run else "run"
    service_contents, timer_contents = _systemd_unit_contents(schedule_time, mode=mode)
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    (SYSTEMD_USER_DIR / SYSTEMD_SERVICE_NAME).write_text(service_contents, encoding="utf-8")
    (SYSTEMD_USER_DIR / SYSTEMD_TIMER_NAME).write_text(timer_contents, encoding="utf-8")

    _run_systemctl("daemon-reload")
    _run_systemctl("enable", "--now", SYSTEMD_TIMER_NAME)
    label = "safe test" if dry_run else "full run"
    print(f"Daily {label} schedule enabled for {schedule_time}.")


def _disable_schedule() -> None:
    result = _run_systemctl("disable", "--now", SYSTEMD_TIMER_NAME, check=False)
    if result.returncode != 0 and result.stderr:
        print(f"  [SCHEDULE WARN] {result.stderr.strip()}")
    else:
        print("Daily schedule disabled.")


def _print_status() -> None:
    print("Accsoft Automation status")
    print(f"  Portal: {LOGIN_URL}")
    print(f"  Username configured: {'yes' if bool(USERNAME) else 'no'}")
    print(f"  OpenRouter key configured: {'yes' if bool(_OR_API_KEY) else 'no'}")
    print(f"  Browser headless: {'yes' if BROWSER_HEADLESS else 'no'}")
    print(f"  Downloads directory: {DOWNLOADS_DIR}")
    print(f"  Answers directory: {ANSWERS_DIR}")
    print(f"  Daily schedule: {_load_schedule_time()}")
    print(f"  Log file: {LOG_PATH}")


def main() -> None:
    args = _parse_args()
    _configure_logging()
    LOGGER.info("command started mode=%s scheduled=%s", args.mode, args.scheduled)

    if args.mode == "setup":
        _setup_local_credentials()
        LOGGER.info("setup completed")
        return

    _validate_configuration()

    if args.mode == "status":
        _print_status()
        LOGGER.info("status completed")
        return

    if args.mode in ("enable", "enable-test"):
        _enable_schedule(dry_run=args.mode == "enable-test")
        LOGGER.info("schedule enabled mode=%s", "test" if args.mode == "enable-test" else "run")
        return

    if args.mode == "disable":
        _disable_schedule()
        LOGGER.info("schedule disabled")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=BROWSER_HEADLESS)
        page = browser.new_page()

        try:
            login(page)
            navigate_to_assignments(page)
            targets = extract_assignments(page)
            open_subjects(page, targets, dry_run=args.mode == "test")
            print("\nPhase 3.2 complete. Browser stays open for 5 seconds...")
            page.wait_for_timeout(BROWSER_CLOSE_DELAY_MS)
            LOGGER.info("automation completed mode=%s subjects=%d", args.mode, len(targets))
        except Exception as e:
            LOGGER.exception("automation failed mode=%s", args.mode)
            print(f"\n[ERROR] {e}")
            raise
        finally:
            LOGGER.info("command finished mode=%s", args.mode)
            browser.close()


if __name__ == "__main__":
    main()
