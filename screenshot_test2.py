from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    # Step 1: Access root - should redirect to login
    print("=== Step 1: Root redirects to login ===")
    page.goto("http://localhost:5173/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    print(f"URL: {page.url}")
    assert "login" in page.url, "Not redirected to login!"
    print("[OK] Root -> Login redirect")

    # Step 2: Fill form and submit
    print("\n=== Step 2: Submit login ===")
    page.fill("input[placeholder='请输入用户名']", "admin")
    page.fill("input[placeholder='请输入密码']", "admin123")
    page.click("button:has-text('登 录')")
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    print(f"After login URL: {page.url}")

    token = page.evaluate("localStorage.getItem('token')")
    session = page.evaluate("sessionStorage.getItem('session_authenticated')")
    print(f"localStorage token: {token}")
    print(f"sessionStorage auth: {session}")

    if token:
        print("[OK] Token in localStorage")
    if session:
        print("[OK] Session auth flag set")

    if "login" not in page.url:
        print("[OK] Redirected to dashboard!")
    else:
        print("[FAIL] Still on login page")

    page.screenshot(path="C:/Users/LSJ/Desktop/login_debug.png", full_page=True)

    if token:
        # Step 3: Navigate within SPA (no reload)
        print("\n=== Step 3: SPA navigate to devices ===")
        page.goto("http://localhost:5173/devices")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        print(f"Devices URL: {page.url}")
        if "login" not in page.url:
            print("[OK] SPA navigation works!")
        else:
            print("[FAIL] Redirected back to login")

        # Step 4: Simulate page refresh
        print("\n=== Step 4: Page refresh (simulate new tab) ===")
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        print(f"After refresh URL: {page.url}")
        if "login" in page.url:
            print("[OK] Refresh goes to login - must re-authenticate. Good security!")
            # Login again
            page.fill("input[placeholder='请输入用户名']", "admin")
            page.fill("input[placeholder='请输入密码']", "admin123")
            page.click("button:has-text('登 录')")
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")
            print(f"After re-login URL: {page.url}")
            if "login" not in page.url:
                print("[OK] Re-login successful!")
        else:
            print("[NOTE] Session survived refresh (sessionStorage persisted)")

    print("\n=== ALL TESTS COMPLETE ===")
    browser.close()
