import os
import time
import requests
import pdfplumber
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIG — fill in your real credentials
# ---------------------------------------------------------------------------
LOGIN_URL = "https://accsoft.piemr.edu.in/accsoft_piemr/StudentLogin.aspx"
USERNAME  = "51110106439"
PASSWORD  = "51110106439"

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


def read_file_content(filepath: str) -> str:
    """Extract text from PDF, DOCX, or image. OCR fallback for image-based PDFs."""
    try:
        ext = filepath.lower()

        if ext.endswith(".pdf"):
            text = extract_pdf_text(filepath)
            if not text or len(text.strip()) < 200:
                print("  [WARN] PDF text too short — trying OCR fallback...")
                text = extract_pdf_with_ocr(filepath)
            if not text.strip():
                print("  [WARN] No readable content extracted from PDF")
            return clean_text(text)

        if ext.endswith((".jpg", ".jpeg", ".png")):
            return extract_image_text(filepath)

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
# PHASE 3.5: AI Answer Generation (OpenRouter)
# ---------------------------------------------------------------------------
_OR_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def generate_answer(question: str) -> str:
    if not _OR_API_KEY:
        print("  [AI ERROR] OPENROUTER_API_KEY is missing from .env — skipping answer generation")
        return "Error generating answer"
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {_OR_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://accsoft.piemr.edu.in",
                "X-Title": "Accsoft Automation",
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [{"role": "user", "content": question}],
            },
            timeout=30,
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
        print(f"  [3.5b] PDF created: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"  [3.5b] PDF conversion failed: {e} — falling back to txt")
        return txt_path


# ---------------------------------------------------------------------------
# PHASE 3.6: Upload generated answer file to portal
# ---------------------------------------------------------------------------
def upload_assignment(page, file_path: str) -> None:
    try:
        print(f"  [3.6] Uploading: {file_path}")
        page.locator("a:has-text('Upload'):visible").first.click()

        page.wait_for_selector("input[type='file']", timeout=10000)
        page.set_input_files("input[type='file']", file_path)
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle")

        print("  [3.6] Upload successful")

        # Navigate back to subject page so the assignment loop can continue
        page.go_back()
        page.wait_for_load_state("domcontentloaded")
    except Exception as e:
        print(f"  [3.6] Upload failed: {e}")


# ---------------------------------------------------------------------------
def login(page) -> None:
    """Open the login page, fill credentials, submit, and confirm login."""
    print("[1/4] Navigating to login page...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=120000)

    print("[2/4] Filling credentials...")
    page.wait_for_selector(USERNAME_SELECTOR, state="visible")
    page.fill(USERNAME_SELECTOR, USERNAME)
    page.fill(PASSWORD_SELECTOR, PASSWORD)

    print("[3/4] Submitting login form...")
    page.click(LOGIN_BTN_SELECTOR)

    print("[4/4] Waiting for post-login navigation...")
    try:
        page.wait_for_url("**/ParentDesk1.aspx", wait_until="domcontentloaded", timeout=120000)
        print("      Login successful.")
    except PlaywrightTimeoutError:
        print(f"      Login failed. Current URL: {page.url}")
        raise RuntimeError("Login failed — did not reach ParentDesk1.aspx. Check credentials.")


def navigate_to_assignments(page) -> None:
    """Click Academic tab to expand submenu, then click Assignments."""
    print("[5/6] Clicking Academic tab...")
    academic = page.get_by_text("Academic", exact=True)
    academic.wait_for(state="visible", timeout=120000)
    academic.click()

    print("      Waiting for submenu to expand...")
    page.wait_for_timeout(1500)

    print("[6/6] Clicking Assignments option...")
    assignments = page.get_by_text("Assignments", exact=True)
    assignments.wait_for(state="visible", timeout=120000)
    assignments.click()
    print("      Assignments page loaded successfully.")


def _scan_subject_rows(page) -> list[dict]:
    """
    First pass: scan the assignments table and return a list of dicts for
    rows where new-assignment count > 0.

    Each dict holds:
      - subject:   display name
      - row_index: position in "table tr" (used to re-locate after go_back)
    """
    rows = page.locator("table tr")
    row_count = rows.count()

    # subject_name → {total_new, first_row_index}
    seen: dict[str, dict] = {}

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

        if subject_name not in seen:
            seen[subject_name] = {"total_new": 0, "first_row_index": i}
        seen[subject_name]["total_new"] += new_count

    return [
        {"subject": name, "row_index": info["first_row_index"]}
        for name, info in seen.items()
        if info["total_new"] > 0
    ]


def extract_assignments(page) -> list[dict]:
    """Phase 2: scan and print subjects that have new assignments. Returns targets for Phase 3."""
    print("\n[Phase 2] Waiting for assignments table to load...")
    page.wait_for_timeout(2000)

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
    academic.wait_for(state="visible", timeout=60000)
    academic.click()

    page.wait_for_timeout(1500)

    assignments = page.locator("a:has-text('Assignments')").first
    assignments.wait_for(state="visible", timeout=60000)
    assignments.click()

    page.wait_for_timeout(2000)


def extract_subject_assignments(page, subject_name: str) -> None:
    """
    Phase 3.2: Extract assignment details using data-label selectors.
    Does NOT click anything.
    """
    print(f"\n  [Phase 3.2] Extracting assignments for: {subject_name}")

    try:
        page.wait_for_selector("#ctl00_ContentPlaceHolder1_DataList2", timeout=15000)
    except PlaywrightTimeoutError:
        print("    [warn] Container #ctl00_ContentPlaceHolder1_DataList2 not found.")

    container = page.locator("#ctl00_ContentPlaceHolder1_DataList2")
    rows = container.locator("tr.GreenPage2")
    count = rows.count()
    print(f"    [debug] Rows inside correct container: {count}")

    # Retry once if AJAX content hasn't rendered yet
    if count == 0:
        print("    [debug] No rows found — retrying after 3s...")
        page.wait_for_timeout(3000)
        rows = container.locator("tr.GreenPage2")
        count = rows.count()
        print(f"    [debug] Rows after retry: {count}")

    total_assignments = 0
    print(f"\n  Subject: {subject_name}")

    for i in range(count):
        row = rows.nth(i)
        cells = row.locator("td")
        cell_count = cells.count()

        if cell_count < 5:
            continue

        texts = [cells.nth(j).inner_text().strip() for j in range(cell_count)]

        assign_no = texts[2]
        due_date  = texts[3]

        status_cell = row.locator("td[data-label='Assignment Status']")
        status = status_cell.inner_text().strip()
        if not status:
            status = status_cell.text_content().strip()
        status = status.lower()
        if not status:
            status = "unknown"
        print(f"  Raw status extracted: {status}")

        if not assign_no or not due_date:
            continue

        status_norm = status.lower().strip()
        print(f"  Status: {status_norm}")

        if any(kw in status_norm for kw in ("upload", "submitted", "done")):
            print(f"  Skipping already uploaded assignment: {assign_no}")
            continue

        total_assignments += 1
        print(f"  Assignment {assign_no} | Due: {due_date} | Status: {status}")

        # Phase 3.3: Download assignment file (direct URL — skips postback link)
        os.makedirs("downloads", exist_ok=True)
        download_link = row.locator('a[href*="Upload/Assignment"]')
        if download_link.count() == 0:
            print(f"  No download link found for {assign_no}")
        else:
            try:
                relative_url = download_link.first.get_attribute("href")
                base_url = "https://accsoft.piemr.edu.in/accsoft_piemr/"
                full_url = base_url + relative_url.replace("../", "")
                response = requests.get(full_url)
                filename = full_url.split("/")[-1]
                filepath = f"downloads/{filename}"
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print(f"  Downloaded: {filepath}")

                # Phase 3.4 + 3.5: Extract questions → AI answers → save
                content = read_file_content(filepath)
                if content:
                    questions = extract_questions(content)

                    subject_safe = subject_name.replace(" ", "_").replace("&", "and")
                    ans_folder = f"answers/{subject_safe}"
                    os.makedirs(ans_folder, exist_ok=True)
                    ans_file = f"{ans_folder}/assignment_{assign_no}.txt"

                    print(f"\n  === Assignment {assign_no} ===")
                    with open(ans_file, "a", encoding="utf-8") as f:
                        for q in questions:
                            if len(q.strip()) < 8:
                                continue
                            print(f"\n  Q: {q}")
                            answer = generate_answer(q)
                            print(f"  A: {answer}")
                            f.write(f"Q: {q}\nA: {answer}\n\n")
                            time.sleep(2)
                    print(f"\n  Answers saved → {ans_file}")

                    # Phase 3.5b → 3.6: Convert to PDF then upload
                    pdf_file = convert_txt_to_pdf(ans_file)
                    upload_assignment(page, os.path.abspath(pdf_file))
            except Exception as e:
                print(f"  [warn] Download failed for {assign_no}: {e}")

    if total_assignments == 0:
        print("  No assignments found.")

    print(f"  Total assignments found: {total_assignments}")


def open_subjects(page, targets: list[dict]) -> None:
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
        row_index = t["row_index"]

        # Re-fetch rows fresh (DOM may differ after each navigation)
        rows = page.locator("table tr")
        row = rows.nth(row_index)

        print(f"  Clicking subject: {subject} ...")
        view_button = row.locator("td").nth(2).locator("a, button")
        if view_button.count() == 0:
            view_button = row.locator("a, button").first
        view_button.click()
        print("  Clicked correct subject view button")

        page.wait_for_load_state("domcontentloaded", timeout=60000)

        # Phase 3.2 context guard: wait for old list to detach, then new content to appear
        try:
            page.wait_for_selector("text=New Assignment", state="detached", timeout=10000)
        except PlaywrightTimeoutError:
            print("  [debug] 'New Assignment' text did not detach — may be AJAX partial reload.")

        try:
            page.wait_for_selector('td[data-label="Assign. No."]', timeout=15000)
        except PlaywrightTimeoutError:
            print("  [warn] Assignment rows not found — falling back with 3s wait...")
            page.wait_for_timeout(3000)

        row_count = page.locator('td[data-label="Assign. No."]').count()
        print(f"  Now on subject page, rows: {row_count}")
        print(f"  [debug] Current URL: {page.url}")

        # Phase 3.2: extract assignments from the subject page
        extract_subject_assignments(page, subject)

        # Navigate back via menu — never rely on browser history
        print("\n  Returning to assignments page...")
        _return_to_assignments(page)
        print("  Assignments table reloaded.\n")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            login(page)
            navigate_to_assignments(page)
            targets = extract_assignments(page)
            open_subjects(page, targets)
            print("\nPhase 3.2 complete. Browser stays open for 5 seconds...")
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"\n[ERROR] {e}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
