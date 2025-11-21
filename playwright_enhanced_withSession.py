import asyncio
import random
import json
import os
import traceback
from typing import Optional, Dict, List
from fastapi import FastAPI, Body, HTTPException, Query
from pydantic import BaseModel
from playwright.async_api import async_playwright
import httpx
from datetime import datetime, timedelta

app = FastAPI()



# ============ Configuration ============

USERNAME = "your_email_id"
PASSWORD = "password"
STORAGE_PATH = "linkedin_storage.json/filename"

async def login_and_save_session():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to LinkedIn login
        await page.goto("https://www.linkedin.com/login")

        # Fill login form
        await page.fill('input#username', USERNAME)
        await page.fill('input#password', PASSWORD)

        # Click Sign In button
        await page.click('button[type="submit"]')

        # Wait for home page or navigation after login
        await page.wait_for_selector('nav[aria-label="Primary Navigation"]', timeout=60000)

        # Save storage state for reuse
        await context.storage_state(path=STORAGE_PATH)
        print("Login complete and storage state saved.")

        await browser.close()



class ProxyConfig:
    """Manage proxy pool"""
    PROXY_POOL = [
//Proxies go here
    ]
    
    @staticmethod
    def get_random_proxy() -> Optional[str]:
        if ProxyConfig.PROXY_POOL:
            return random.choice(ProxyConfig.PROXY_POOL)
        return None

class StealthConfig:
    """Advanced stealth techniques"""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    STEALTH_JS = """
    // Override webdriver detection
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    
    // Override plugins
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    
    // Chrome runtime
    window.chrome = {runtime: {}};
    
    // Permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({state: Notification.permission}) :
            originalQuery(parameters)
    );
    
    // Hardware specs
    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
    Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
    
    // Timezone randomization
    Intl.DateTimeFormat.prototype.resolvedOptions = (() => {
        const original = Intl.DateTimeFormat.prototype.resolvedOptions;
        return function(...args) {
            const result = original.apply(this, args);
            result.timeZone = 'America/New_York';
            return result;
        };
    })();
    
    // Canvas fingerprinting protection
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {
        if (this.width === 280 && this.height === 60) {
            return 'data:image/png;base64,FAKE_CANVAS_DATA';
        }
        return originalToDataURL.apply(this, arguments);
    };
    
    // WebGL protection
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.apply(this, arguments);
    };
    """
    
    @staticmethod
    def get_random_user_agent() -> str:
        return random.choice(StealthConfig.USER_AGENTS)

# ============ Session Management ============

SESSION_STORAGE = {}  # In production, use Redis or database

class BrowserSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.request_count = 0
        self.blocked_count = 0
        self.success_count = 0
    
    def should_rotate(self) -> bool:
        """Rotate session if too many requests or time elapsed"""
        age = datetime.now() - self.created_at
        return self.request_count > 50 or age > timedelta(hours=2)

def get_or_create_session(session_id: str) -> BrowserSession:
    if session_id not in SESSION_STORAGE:
        SESSION_STORAGE[session_id] = BrowserSession(session_id)
    return SESSION_STORAGE[session_id]

# ============ CAPTCHA Solving ============

async def solve_captcha_if_needed(page, timeout_ms: int = 10000) -> bool:
    """
    Detect and attempt to solve CAPTCHAs.
    You can integrate with:
    - 2Captcha API
    - Anti-Captcha
    - DeathByCaptcha
    - AI-based solutions
    """
    try:
        # Check for reCAPTCHA v2
        recaptcha_v2 = await page.query_selector('[data-sitekey]')
        if recaptcha_v2:
            print("[CAPTCHA] reCAPTCHA v2 detected, attempting solve...")
            # Integrate with 2Captcha or similar
            # For now, just wait for manual solve
            await page.wait_for_timeout(timeout_ms)
            return True
        
        # Check for reCAPTCHA v3 (invisible)
        recaptcha_v3_script = await page.content()
        if 'recaptcha/api.js' in recaptcha_v3_script:
            print("[CAPTCHA] reCAPTCHA v3 detected")
            await page.wait_for_timeout(2000)
            return True
        
        return False
    except Exception as e:
        print(f"CAPTCHA check warning: {e}")
        return False

# ============ Block Detection & Retry ============

def detect_block_indicators(html: str, text: str) -> Dict:
    """Detect various types of blocks and rate limits"""
    indicators = {
        "blocked": False,
        "block_type": None,
        "retry_after": None
    }
    
    block_keywords = {
        "captcha": ["captcha", "recaptcha", "challenge"],
        "rate_limit": ["rate limit", "too many requests", "429", "slow down"],
        "ip_blocked": ["access denied", "ip blocked", "forbidden", "403"],
        "js_required": ["enable javascript", "js required"],
        "bot_check": ["verify you're human", "bot detection", "automated access"],
    }
    
    combined = (html + text).lower()
    
    for block_type, keywords in block_keywords.items():
        if any(keyword in combined for keyword in keywords):
            indicators["blocked"] = True
            indicators["block_type"] = block_type
            break
    
    return indicators

# ============ Main Scraping Function ============

class CrawlRequest(BaseModel):
    url: str
    selector: Optional[str] = None
    wait_for_selector: Optional[str] = None
    add_delays: bool = True
    session_id: Optional[str] = None
    max_retries: int = 3

async def linkedin_authenticated_scrape(url: str, max_jobs: int = 20, storage_path: str = "linkedin_storage.json"):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-extensions",
                "--no-first-run",
            ])
        proxy = ProxyConfig.get_random_proxy()
        context_opts = {
            "user_agent": StealthConfig.get_random_user_agent(),
            "locale": "en-US",
            "viewport": {"width": 1920, "height": 1080},
            "timezone_id": "America/New_York",
            "storage_state": storage_path,
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "DNT": "1",
                "Referer": "https://www.google.com/",
            }
        }
        if proxy:
            context_opts["proxy"] = {"server": proxy}
        
        context = await browser.new_context(**context_opts)
        page = await context.new_page()

        await page.evaluate(StealthConfig.STEALTH_JS)

        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(3, 6))

        for _ in range(6):
            await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await asyncio.sleep(random.uniform(1, 2))

        page_html = await page.content()
        page_text = await page.evaluate("() => document.body.innerText")
        block_info = detect_block_indicators(page_html, page_text)
        if block_info["blocked"]:
            await context.close()
            await browser.close()
            return {
                "status": "blocked",
                "message": f"Blocked detected: {block_info['block_type']}"
            }

        job_cards = await page.query_selector_all(".base-card")
        jobs = []
        for card in job_cards[:max_jobs]:
            try:
                title = await card.query_selector_eval(".base-search-card__title", "el => el.innerText") or ""
                company = await card.query_selector_eval(".base-search-card__subtitle", "el => el.innerText") or ""
                location = await card.query_selector_eval(".job-search-card__location", "el => el.innerText") or ""
                description = await card.query_selector_eval(".show-more-less-html__markup", "el => el.innerText") or ""
                apply_url = await card.query_selector_eval("a.base-card__full-link", "el => el.href") or ""
                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": location.strip(),
                    "description_summary": description.strip(),
                    "application_link": apply_url.strip(),
                })
            except Exception:
                continue
        await context.close()
        await browser.close()
        return {"status": "success", "count": len(jobs), "jobs": jobs}


async def linkedin_enhanced_scrape(url: str, max_jobs: int = 20):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-extensions",
                "--no-first-run",
            ])
        context = await browser.new_context(
            user_agent=random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"]),
            locale="en-US",
            viewport={"width": 1920, "height": 1080},
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "DNT": "1",
                "Referer": "https://www.google.com/",
            }
        )
        page = await context.new_page()

        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = {runtime: {}};
        """
        await page.evaluate(stealth_js)

        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(3, 6))
        
        # Scroll page to load lazy content
        for _ in range(6):
            await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await asyncio.sleep(random.uniform(1, 2))

        page_text = await page.evaluate("() => document.body.innerText")
        print("---- PAGE TEXT SNIPPET ----")
        print(page_text[:2000])
        print("---------------------------")

        # Try multiple possible job card selectors
        selectors_to_try = [
            ".base-card",
            ".jobs-search-results__list-item",
            "[data-occludable-job-id]",
            ".result-card.job-result-card"
        ]
        
        job_cards = []
        for selector in selectors_to_try:
            cards = await page.query_selector_all(selector)
            if cards and len(cards) > 0:
                print(f"Using job card selector: {selector}, found {len(cards)} cards")
                job_cards = cards
                break
        
        print(f"Total job cards found: {len(job_cards)}")

        # Log outer html for first few cards
        for i, card in enumerate(job_cards[:3]):
            outer_html = await card.evaluate("(el) => el.outerHTML")
            print(f"Job card {i+1} HTML snippet: {outer_html[:600]}")
        
        jobs = []
        for card in job_cards[:max_jobs]:
            try:
                title = await card.query_selector_eval(".base-search-card__title", "el => el.innerText") or ""
                company = await card.query_selector_eval(".base-search-card__subtitle", "el => el.innerText") or ""
                location = await card.query_selector_eval(".job-search-card__location", "el => el.innerText") or ""
                description = await card.query_selector_eval(".show-more-less-html__markup", "el => el.innerText") or ""
                apply_url = await card.query_selector_eval("a.base-card__full-link", "el => el.href") or ""

                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": location.strip(),
                    "description_summary": description.strip(),
                    "application_link": apply_url.strip(),
                })
            except Exception as e:
                print(f"Error extracting job card: {e}")
                continue

        await context.close()
        await browser.close()
        return jobs



@app.post("/crawl")
async def crawl_with_self_hosted(request: CrawlRequest):
    """
    Self-hosted scraping with:
    - Proxy rotation
    - CAPTCHA detection & solving
    - Session management
    - Block detection & retry
    - Advanced stealth
    """

    session_id = request.session_id or f"session_{random.randint(10000, 99999)}"
    session = get_or_create_session(session_id)

    for attempt in range(request.max_retries):
        browser = None
        context = None
        try:
            user_agent = StealthConfig.get_random_user_agent()
            proxy = ProxyConfig.get_random_proxy()

            async with async_playwright() as pw:
                print(f"[Attempt {attempt + 1}] Launching browser with proxy: {proxy}")

                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--window-size=1920,1080",
                        "--start-maximized",
                        "--disable-extensions",
                        "--no-first-run",
                    ]
                )

                # Create context with realistic headers
                context = await browser.new_context(
                    user_agent=user_agent,
                    locale="en-US",
                    timezone_id="America/New_York",
                    viewport={"width": 1920, "height": 1080},
                    proxy={"server": proxy} if proxy else None,
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Referer": "https://www.google.com/",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )

                page = await context.new_page()

                # Block unnecessary resources
                await page.route(
                    "**/*",
                    lambda route: asyncio.create_task(
                        route.abort() if route.request.resource_type in [
                            "image", "stylesheet", "font", "media"
                        ] else route.continue_()
                    )
                )

                # Inject stealth JS
                await page.evaluate(StealthConfig.STEALTH_JS)

                # Random initial delay
                if request.add_delays:
                    await asyncio.sleep(random.uniform(2, 4))

                # Navigate
                print(f"[Navigating] {request.url}")
                try:
                    await page.goto(
                        request.url,
                        wait_until="domcontentloaded",
                        timeout=random.randint(20000, 40000)
                    )
                except Exception as nav_err:
                    print(f"Navigation warning: {nav_err}")

                # Page settle wait
                await page.wait_for_timeout(random.randint(2000, 4000))

                # CAPTCHA detection
                captcha_detected = await solve_captcha_if_needed(page)
                if captcha_detected:
                    print(f"[CAPTCHA] Detected on {request.url}")
                    await page.wait_for_timeout(random.randint(1000, 2000))

                # Human-like behavior
                if request.add_delays:
                    for _ in range(random.randint(2, 4)):
                        scroll_amount = random.randint(100, 800)
                        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                        await asyncio.sleep(random.uniform(0.3, 1.0))
                    await page.evaluate("window.scrollTo(0, 0)")

                # Get page content
                page_html = await page.content()
                page_text = await page.evaluate('() => document.body.innerText')

                # Block detection
                block_info = detect_block_indicators(page_html, page_text)
                if block_info["blocked"]:
                    session.blocked_count += 1
                    print(f"[Block Detected] {block_info['block_type']}")
                    if attempt < request.max_retries - 1:
                        await asyncio.sleep(random.uniform(5, 10) * (attempt + 1))
                        await context.close()
                        await browser.close()
                        continue
                    else:
                        await context.close()
                        await browser.close()
                        return {
                            "status": "blocked",
                            "block_type": block_info["block_type"],
                            "error": f"Blocked detected: {block_info['block_type']}",
                            "url": request.url,
                            "session_id": session_id,
                        }

                # Extract text by selector if provided
                content = page_text
                links = []
                if request.selector:
                    try:
                        elements = await page.query_selector_all(request.selector)
                        for elem in elements[:100]:
                            text = await elem.inner_text()
                            href = await elem.get_attribute('href')
                            if href:
                                links.append({"text": text.strip(), "href": href})
                        content = "\n".join([f"{l['text']}: {l['href']}" for l in links])
                    except Exception as sel_err:
                        print(f"Selector extraction warning: {sel_err}")

                session.success_count += 1
                session.request_count += 1

                await context.close()
                await browser.close()

                return {
                    "status": "success",
                    "url": request.url,
                    "content": content[:5000],
                    "links": links,
                    "captcha_detected": captcha_detected,
                    "blocked": block_info["blocked"],
                    "block_type": block_info.get("block_type"),
                    "session_id": session_id,
                }

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            session.blocked_count += 1
            if context:
                await context.close()
            if browser:
                await browser.close()

            if attempt == request.max_retries - 1:
                return {
                    "status": "error",
                    "error": str(e),
                    "url": request.url,
                    "session_id": session_id,
                    "attempts": request.max_retries
                }

            # Exponential backoff
            await asyncio.sleep(random.uniform(3, 7) * (attempt + 1))

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
