from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

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
        status    = texts[-1]

        if not assign_no or not due_date:
            continue

        total_assignments += 1
        print(f"  Assignment {assign_no} | Due: {due_date} | Status: {status}")

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
