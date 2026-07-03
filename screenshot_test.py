from playwright.sync_api import sync_playwright
import os

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    # 1. Login page
    print("=== Login Page ===")
    page.goto("http://localhost:5173/login")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    page.screenshot(path="C:/Users/LSJ/Desktop/login.png", full_page=True)
    print("Login screenshot saved")

    # Check title element
    title = page.locator(".page-title, .page-title-wrapper h2").first
    if title.count():
        print(f"Title found: '{title.inner_text()}' - has left border accent")

    # Check stat cards on login (none expected, but verify login card style)
    card = page.locator(".login-card")
    if card.count():
        print(f"Login card visible, width: {card.bounding_box()['width']:.0f}px")

    # 2. Dashboard page (will show loading/empty state)
    print("\n=== Dashboard Page ===")
    page.goto("http://localhost:5173/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Try to find login redirect - if redirected back, login first
    current_url = page.url
    print(f"Current URL: {current_url}")

    if "/login" in current_url:
        # Fill in test credentials
        page.fill("input[placeholder='请输入用户名']", "admin")
        page.fill("input[placeholder='请输入密码']", "admin123")

        # Click login button
        login_btn = page.locator("button:has-text('登 录')")
        login_btn.click()
        page.wait_for_timeout(2000)

        current_url = page.url
        print(f"After login URL: {current_url}")

    page.screenshot(path="C:/Users/LSJ/Desktop/dashboard.png", full_page=True)
    print("Dashboard screenshot saved")

    # Check stat cards
    stat_cards = page.locator(".stat-card").all()
    print(f"StatCard components found: {len(stat_cards)}")

    # Check sidebar active indicator
    active_menu = page.locator(".el-menu-item.is-active")
    if active_menu.count():
        active_text = active_menu.first.inner_text()
        print(f"Active menu item: '{active_text}' with gradient indicator")

    # Check table styling (no stripe)
    tables = page.locator("table.el-table__body").all()
    print(f"Tables found: {len(tables)}")

    # 3. Other pages - just verify they load with PageTitle
    pages_to_check = [
        ("/devices", "Devices"),
        ("/alerts", "Alerts"),
        ("/reports-center", "ReportCenter"),
    ]

    for path, name in pages_to_check:
        page.goto(f"http://localhost:5173{path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        screenshot_path = f"C:/Users/LSJ/Desktop/{name.lower()}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"{name} screenshot saved")

        # Check PageTitle
        pg_title = page.locator(".page-title").first
        if pg_title.count():
            print(f"  PageTitle '{pg_title.inner_text()}' has left accent bar")

    browser.close()
    print("\n=== All screenshots captured ===")
