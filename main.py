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
ASSIGNMENTS_LINK    = "#PLACEHOLDER_assignments_nav"  # nav link to Assignments section
ASSIGNMENTS_PAGE_EL = "#PLACEHOLDER_assignments_page" # element confirming Assignments page loaded


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
        page.wait_for_url("**/ParentDesk1.aspx", wait_until="domcontentloaded", timeout=60000)
        print("      Login successful.")
    except PlaywrightTimeoutError:
        print(f"      Login failed. Current URL: {page.url}")
        raise RuntimeError("Login failed — did not reach ParentDesk1.aspx. Check credentials.")


def navigate_to_assignments(page) -> None:
    """Click the Assignments nav link and wait for the page to load."""
    print("[5/6] Clicking Assignments link...")
    try:
        page.wait_for_selector(ASSIGNMENTS_LINK, state="visible", timeout=10000)
        page.click(ASSIGNMENTS_LINK)
    except PlaywrightTimeoutError:
        raise RuntimeError(
            f"Assignments link '{ASSIGNMENTS_LINK}' not found. Update ASSIGNMENTS_LINK selector."
        )

    print("[6/6] Waiting for Assignments page to load...")
    try:
        page.wait_for_selector(ASSIGNMENTS_PAGE_EL, state="visible", timeout=10000)
        print("      Assignments page loaded successfully.")
    except PlaywrightTimeoutError:
        raise RuntimeError(
            f"Assignments page element '{ASSIGNMENTS_PAGE_EL}' not found. "
            "Update ASSIGNMENTS_PAGE_EL selector."
        )


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
