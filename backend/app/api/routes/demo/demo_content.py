"""
Pre-written demo content for the Demo page.
Streamed token-by-token to simulate real-time AI generation.
"""

DEMO_ACCEPTANCE_CRITERIA = [
    "Navigate to Amazon.com homepage and verify page loads correctly with all major UI elements visible",
    "Verify global search bar is visible, enabled, and accepts keyboard input",
    "Search for 'wireless mouse' and verify relevant product results are displayed",
    "Verify product cards display title, price, rating, and thumbnail image correctly",
    "Apply price-based sorting (Low to High) and verify results reorder accordingly",
    "Search for a second product category ('usb keyboard') and verify new results are shown",
    "Search for a third product category ('laptop stand') and verify results with image thumbnails",
    "Navigate to cart page and verify the shopping cart loads correctly",
]

DEMO_TEST_CASES_TEXT = """\
## Test Suite: Amazon Shopping Flow — End-to-End Validation

**Application Under Test:** Amazon.com
**Test Environment:** Production (https://www.amazon.com)
**Browser:** Chromium (via Playwright)  |  Viewport: 1280 × 800
**Search Queries:** "wireless mouse", "usb keyboard", "laptop stand"

---

### TC-001: Homepage Navigation and Load Verification
**Type:** Positive | **Priority:** P0 - Critical | **Category:** Navigation

**Preconditions:** Browser is open with stable internet

**Test Steps:**
1. Navigate to https://www.amazon.com
2. Wait for DOM content loaded
3. Verify page title contains "Amazon"

**Expected Result:** Page loads without errors; title includes "Amazon"

---

### TC-002: Search Bar Visibility and Accessibility
**Type:** Positive | **Priority:** P0 - Critical | **Category:** UI Verification

**Test Steps:**
1. Locate the search input (#twotabsearchtextbox)
2. Verify it is visible and enabled

**Expected Result:** Search bar is visible and ready for input

---

### TC-003: Navigation Bar Links Present
**Type:** Positive | **Priority:** P1 - High | **Category:** UI Verification

**Test Steps:**
1. Verify the Amazon logo is visible
2. Verify the Cart icon link is visible
3. Verify the Account & Lists element is present

**Expected Result:** All major navigation elements are visible

---

### TC-004: Search for "wireless mouse"
**Type:** Positive | **Priority:** P0 - Critical | **Category:** Core Functionality

**Test Steps:**
1. Type "wireless mouse" into the search bar
2. Click the search submit button
3. Wait for results to load

**Expected Result:** Search results page displays product listings

---

### TC-005: Search Results Count Validation
**Type:** Positive | **Priority:** P1 - High | **Category:** Data Verification

**Test Steps:**
1. Count visible product result cards
2. Verify count is greater than 5

**Expected Result:** Multiple product cards are displayed

---

### TC-006: Product Card Title Verification
**Type:** Positive | **Priority:** P1 - High | **Category:** Content Validation

**Test Steps:**
1. Locate the first product card
2. Extract the product title text
3. Verify title is non-empty

**Expected Result:** Product card contains a readable title

---

### TC-007: Product Card Price Verification
**Type:** Positive | **Priority:** P1 - High | **Category:** Content Validation

**Test Steps:**
1. Locate the price element on the first product card
2. Extract the price text
3. Verify a currency value is present

**Expected Result:** Product price is displayed in valid currency format

---

### TC-008: Product Card Rating Stars Visible
**Type:** Positive | **Priority:** P2 - Medium | **Category:** Content Validation

**Test Steps:**
1. Locate the star rating element on the first product card
2. Verify it is visible

**Expected Result:** Star rating is displayed on the product card

---

### TC-009: Voice Search Button Availability (Expected FAIL)
**Type:** Negative | **Priority:** P2 - Medium | **Category:** Feature Verification

**Test Steps:**
1. Look for a microphone / voice search button next to the search bar
2. Attempt to verify it is visible within 3 seconds

**Expected Result:** ⚠️ Expected to FAIL — voice search is not available on desktop web

---

### TC-010: Sort by Price Low to High
**Type:** Positive | **Priority:** P1 - High | **Category:** Sorting

**Test Steps:**
1. Click the sort dropdown
2. Select "Price: Low to High"
3. Wait for page to reload
4. Verify search results are still displayed

**Expected Result:** Results are reordered by ascending price

---

### TC-011: Search for Second Product — "usb keyboard"
**Type:** Positive | **Priority:** P0 - Critical | **Category:** Core Functionality

**Test Steps:**
1. Navigate back to Amazon homepage
2. Type "usb keyboard" into the search bar
3. Submit the search
4. Verify results are displayed

**Expected Result:** New search results for "usb keyboard" are shown

---

### TC-012: Second Search — Results Relevance
**Type:** Positive | **Priority:** P1 - High | **Category:** Content Validation

**Test Steps:**
1. Extract the title of the first result
2. Verify the title contains "keyboard" or "usb" (case-insensitive)

**Expected Result:** Results are relevant to the "usb keyboard" query

---

### TC-013: Navigate to Cart Page
**Type:** Positive | **Priority:** P0 - Critical | **Category:** Navigation

**Test Steps:**
1. Click the cart icon in the navigation bar (#nav-cart)
2. Wait for the cart page to load
3. Verify the URL contains "/cart" or "gp/cart"

**Expected Result:** Cart page loads successfully

---

### TC-014: "Try Before You Buy" on Cart Page (Expected FAIL)
**Type:** Negative | **Priority:** P2 - Medium | **Category:** Feature Verification

**Test Steps:**
1. Navigate to cart page
2. Look for "Try Before You Buy" option text
3. Attempt to verify it is visible within 3 seconds

**Expected Result:** ⚠️ Expected to FAIL — electronics products don't support Try Before You Buy

---

### TC-015: Search for Third Product — "laptop stand"
**Type:** Positive | **Priority:** P1 - High | **Category:** Core Functionality

**Test Steps:**
1. Navigate back to homepage
2. Search for "laptop stand"
3. Verify results are displayed

**Expected Result:** Search results for "laptop stand" are shown

---

### TC-016: Product Image Thumbnails
**Type:** Positive | **Priority:** P1 - High | **Category:** Content Validation

**Test Steps:**
1. Locate the first product card in results
2. Verify a product thumbnail image is visible
3. Verify the image src attribute is valid

**Expected Result:** Product card includes a visible image thumbnail

---

### Test Suite Summary

| ID     | Test Case                              | Type     | Priority | Expected |
|--------|----------------------------------------|----------|----------|----------|
| TC-001 | Homepage Navigation                    | Positive | P0       | ✅ Pass  |
| TC-002 | Search Bar Visibility                  | Positive | P0       | ✅ Pass  |
| TC-003 | Navigation Bar Links                   | Positive | P1       | ✅ Pass  |
| TC-004 | Search for Wireless Mouse              | Positive | P0       | ✅ Pass  |
| TC-005 | Search Results Count                   | Positive | P1       | ✅ Pass  |
| TC-006 | Product Card Title                     | Positive | P1       | ✅ Pass  |
| TC-007 | Product Card Price                     | Positive | P1       | ✅ Pass  |
| TC-008 | Product Card Rating Stars              | Positive | P2       | ✅ Pass  |
| TC-009 | Voice Search Button                    | Negative | P2       | ❌ Fail  |
| TC-010 | Sort by Price Low to High              | Positive | P1       | ✅ Pass  |
| TC-011 | Search for USB Keyboard                | Positive | P0       | ✅ Pass  |
| TC-012 | Second Search Relevance                | Positive | P1       | ✅ Pass  |
| TC-013 | Navigate to Cart Page                  | Positive | P0       | ✅ Pass  |
| TC-014 | Try Before You Buy                     | Negative | P2       | ❌ Fail  |
| TC-015 | Search for Laptop Stand                | Positive | P1       | ✅ Pass  |
| TC-016 | Product Image Thumbnails               | Positive | P1       | ✅ Pass  |

**Total: 16 Test Cases** — 14 Expected Pass | 2 Expected Fail
"""


DEMO_SCRIPT_TEXT = """\
# ─────────────────────────────────────────────────────────
# Amazon Shopping Flow — Playwright Test Script
# Generated by AI Test Automation System
# 16 Test Cases | Target: https://www.amazon.com
# ─────────────────────────────────────────────────────────

import asyncio
from playwright.async_api import async_playwright


async def run_amazon_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=1000
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = await context.new_page()
        page.set_default_timeout(12000)

        results = []

        # ── TC-001: Homepage Navigation ─────────────────────
        try:
            await page.goto("https://www.amazon.com/?language=en_US", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            title = await page.title()
            assert "amazon" in title.lower(), f"Expected 'Amazon' in title, got: {title}"
            results.append(("TC-001", "Homepage Navigation", "PASSED"))
            print("  ✅ TC-001: Homepage Navigation — PASSED")
        except Exception as e:
            results.append(("TC-001", "Homepage Navigation", f"FAILED: {e}"))
            print(f"  ❌ TC-001: Homepage Navigation — FAILED: {e}")

        # ── TC-002: Search Bar Visibility ────────────────────
        try:
            search_box = page.locator("#twotabsearchtextbox")
            await search_box.wait_for(state="visible", timeout=5000)
            assert await search_box.is_enabled(), "Search bar is not enabled"
            results.append(("TC-002", "Search Bar Visibility", "PASSED"))
            print("  ✅ TC-002: Search Bar Visibility — PASSED")
        except Exception as e:
            results.append(("TC-002", "Search Bar Visibility", f"FAILED: {e}"))
            print(f"  ❌ TC-002: Search Bar Visibility — FAILED: {e}")

        # ── TC-003: Navigation Bar Links ─────────────────────
        try:
            logo = page.locator("#nav-logo-sprites")
            await logo.wait_for(state="visible", timeout=5000)
            cart = page.locator("#nav-cart")
            await cart.wait_for(state="visible", timeout=3000)
            results.append(("TC-003", "Navigation Bar Links", "PASSED"))
            print("  ✅ TC-003: Navigation Bar Links — PASSED")
        except Exception as e:
            results.append(("TC-003", "Navigation Bar Links", f"FAILED: {e}"))
            print(f"  ❌ TC-003: Navigation Bar Links — FAILED: {e}")

        # ── TC-004: Search for "wireless mouse" ─────────────
        try:
            await page.fill("#twotabsearchtextbox", "wireless mouse")
            await page.click("#nav-search-submit-button")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_selector(
                "[data-component-type='s-search-result']", timeout=10000
            )
            results.append(("TC-004", "Search — Wireless Mouse", "PASSED"))
            print("  ✅ TC-004: Search — Wireless Mouse — PASSED")
        except Exception as e:
            results.append(("TC-004", "Search — Wireless Mouse", f"FAILED: {e}"))
            print(f"  ❌ TC-004: Search — Wireless Mouse — FAILED: {e}")

        # ── TC-005: Search Results Count ─────────────────────
        try:
            items = page.locator("[data-component-type='s-search-result']")
            count = await items.count()
            assert count > 5, f"Expected results > 5, got {count}"
            results.append(("TC-005", "Search Results Count", "PASSED"))
            print(f"  ✅ TC-005: Search Results Count — PASSED ({count} items)")
        except Exception as e:
            results.append(("TC-005", "Search Results Count", f"FAILED: {e}"))
            print(f"  ❌ TC-005: Search Results Count — FAILED: {e}")

        # ── TC-006: Product Card Title ───────────────────────
        try:
            first = page.locator("[data-component-type='s-search-result']").first
            title_el = first.locator("h2")
            await title_el.wait_for(state="visible", timeout=5000)
            title_text = (await title_el.inner_text()).strip()
            assert len(title_text) > 0, "Product title is empty"
            results.append(("TC-006", "Product Card Title", "PASSED"))
            print("  ✅ TC-006: Product Card Title — PASSED")
        except Exception as e:
            results.append(("TC-006", "Product Card Title", f"FAILED: {e}"))
            print(f"  ❌ TC-006: Product Card Title — FAILED: {e}")

        # ── TC-007: Product Card Price ───────────────────────
        try:
            first = page.locator("[data-component-type='s-search-result']").first
            price_whole = first.locator(".a-price-whole").first
            await price_whole.wait_for(state="visible", timeout=5000)
            price_text = (await price_whole.inner_text()).strip()
            assert len(price_text) > 0, "Price is empty"
            results.append(("TC-007", "Product Card Price", "PASSED"))
            print(f"  ✅ TC-007: Product Card Price — PASSED")
        except Exception as e:
            results.append(("TC-007", "Product Card Price", f"FAILED: {e}"))
            print(f"  ❌ TC-007: Product Card Price — FAILED: {e}")

        # ── TC-008: Product Card Rating Stars ────────────────
        try:
            first = page.locator("[data-component-type='s-search-result']").first
            rating = first.locator("[data-cy='reviews-ratings-slot'], .a-icon-star-small, [aria-label*='out of 5 stars']").first
            await rating.wait_for(state="visible", timeout=5000)
            results.append(("TC-008", "Product Card Rating Stars", "PASSED"))
            print("  ✅ TC-008: Product Card Rating Stars — PASSED")
        except Exception as e:
            results.append(("TC-008", "Product Card Rating Stars", f"FAILED: {e}"))
            print(f"  ❌ TC-008: Product Card Rating Stars — FAILED: {e}")

        # ── TC-009: Voice Search Button (Expected FAIL) ─────
        try:
            mic_btn = page.locator("#nav-search-submit-button ~ [aria-label*='voice'], .nav-mic-button, #voice-search-button")
            await mic_btn.wait_for(state="visible", timeout=3000)
            assert await mic_btn.is_visible(), "Voice search button not found"
            results.append(("TC-009", "Voice Search Button", "PASSED"))
            print("  ✅ TC-009: Voice Search Button — PASSED")
        except Exception as e:
            results.append(("TC-009", "Voice Search Button", f"FAILED: {e}"))
            print(f"  ❌ TC-009: Voice Search Button — FAILED: {e}")

        # ── TC-010: Sort by Price Low to High ────────────────
        try:
            sort_dropdown = page.locator("#s-result-sort-select, [aria-label='Sort by:']").first
            await sort_dropdown.wait_for(state="visible", timeout=5000)
            await page.select_option("#s-result-sort-select", "price-asc-rank")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_selector(
                "[data-component-type='s-search-result']", timeout=10000
            )
            results.append(("TC-010", "Sort by Price Low to High", "PASSED"))
            print("  ✅ TC-010: Sort by Price Low to High — PASSED")
        except Exception as e:
            results.append(("TC-010", "Sort by Price Low to High", f"FAILED: {e}"))
            print(f"  ❌ TC-010: Sort by Price Low to High — FAILED: {e}")

        # ── TC-011: Search for "usb keyboard" ────────────────
        try:
            await page.goto("https://www.amazon.com", wait_until="domcontentloaded")
            await page.fill("#twotabsearchtextbox", "usb keyboard")
            await page.click("#nav-search-submit-button")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_selector(
                "[data-component-type='s-search-result']", timeout=10000
            )
            results.append(("TC-011", "Search — USB Keyboard", "PASSED"))
            print("  ✅ TC-011: Search — USB Keyboard — PASSED")
        except Exception as e:
            results.append(("TC-011", "Search — USB Keyboard", f"FAILED: {e}"))
            print(f"  ❌ TC-011: Search — USB Keyboard — FAILED: {e}")

        # ── TC-012: Second Search Relevance ──────────────────
        try:
            first = page.locator("[data-component-type='s-search-result']").first
            title_text = (await first.locator("h2").inner_text()).strip().lower()
            assert "keyboard" in title_text or "usb" in title_text, \
                f"Result not relevant: {title_text[:80]}"
            results.append(("TC-012", "Second Search Relevance", "PASSED"))
            print("  ✅ TC-012: Second Search Relevance — PASSED")
        except Exception as e:
            results.append(("TC-012", "Second Search Relevance", f"FAILED: {e}"))
            print(f"  ❌ TC-012: Second Search Relevance — FAILED: {e}")

        # ── TC-013: Navigate to Cart Page ────────────────────
        try:
            await page.click("#nav-cart")
            await page.wait_for_load_state("domcontentloaded")
            assert "cart" in page.url.lower() or "gp/cart" in page.url.lower(), \
                f"Not on cart page: {page.url}"
            results.append(("TC-013", "Navigate to Cart Page", "PASSED"))
            print("  ✅ TC-013: Navigate to Cart Page — PASSED")
        except Exception as e:
            results.append(("TC-013", "Navigate to Cart Page", f"FAILED: {e}"))
            print(f"  ❌ TC-013: Navigate to Cart Page — FAILED: {e}")

        # ── TC-014: Try Before You Buy (Expected FAIL) ──────
        try:
            await page.goto("https://www.amazon.com/gp/cart/view.html", wait_until="domcontentloaded")
            tbb = page.get_by_text("Try Before You Buy")
            await tbb.first.wait_for(state="visible", timeout=3000)
            results.append(("TC-014", "Try Before You Buy", "PASSED"))
            print("  ✅ TC-014: Try Before You Buy — PASSED")
        except Exception as e:
            results.append(("TC-014", "Try Before You Buy", f"FAILED: {e}"))
            print(f"  ❌ TC-014: Try Before You Buy — FAILED: {e}")

        # ── TC-015: Search for "laptop stand" ────────────────
        try:
            await page.goto("https://www.amazon.com", wait_until="domcontentloaded")
            await page.fill("#twotabsearchtextbox", "laptop stand")
            await page.click("#nav-search-submit-button")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_selector(
                "[data-component-type='s-search-result']", timeout=10000
            )
            results.append(("TC-015", "Search — Laptop Stand", "PASSED"))
            print("  ✅ TC-015: Search — Laptop Stand — PASSED")
        except Exception as e:
            results.append(("TC-015", "Search — Laptop Stand", f"FAILED: {e}"))
            print(f"  ❌ TC-015: Search — Laptop Stand — FAILED: {e}")

        # ── TC-016: Product Image Thumbnails ─────────────────
        try:
            first = page.locator("[data-component-type='s-search-result']").first
            img = first.locator("img.s-image").first
            await img.wait_for(state="visible", timeout=5000)
            src = await img.get_attribute("src")
            assert src and len(src) > 10, f"Image src is invalid: {src}"
            results.append(("TC-016", "Product Image Thumbnails", "PASSED"))
            print("  ✅ TC-016: Product Image Thumbnails — PASSED")
        except Exception as e:
            results.append(("TC-016", "Product Image Thumbnails", f"FAILED: {e}"))
            print(f"  ❌ TC-016: Product Image Thumbnails — FAILED: {e}")

        # ── Summary ──────────────────────────────────────────
        passed = sum(1 for r in results if r[2] == "PASSED")
        failed = len(results) - passed
        print(f"\\n{'='*55}")
        print(f"  Results: {passed} Passed | {failed} Failed | {len(results)} Total")
        print(f"{'='*55}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_amazon_tests())
"""
