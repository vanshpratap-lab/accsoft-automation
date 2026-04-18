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


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            login(page)
            navigate_to_assignments(page)
            print("\nPhase 1 complete. Browser stays open for 5 seconds...")
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"\n[ERROR] {e}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
