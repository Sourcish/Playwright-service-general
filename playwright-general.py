from fastapi import FastAPI, Body
from pydantic import BaseModel
import os
import uvicorn
import random
import asyncio
from playwright.async_api import async_playwright


app = FastAPI()

class CrawlRequest(BaseModel):
    url: str
    selector: str = None
    add_delays: bool = True

# User-Agent rotation list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

async def apply_human_behavior(page, delay_ms: int = 500):
    """Simulate human-like browsing behavior"""
    try:
        await page.evaluate(f"window.scrollBy(0, {random.randint(100, 500)})")
        await asyncio.sleep(random.uniform(0.5, 2.0))
        await page.evaluate("window.scrollTo(0, 0)")
    except:
        pass

def detect_captcha(content: str) -> bool:
    """Detect common CAPTCHA indicators"""
    captcha_keywords = [
        "captcha", "recaptcha", "challenge", "verify you're human",
        "bot check", "security check", "unusual activity"
    ]
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in captcha_keywords)

@app.post("/crawl")
async def crawl_page(request: CrawlRequest = Body(...)):
    url = request.url
    selector = request.selector
    add_delays = request.add_delays
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )
            
            user_agent = random.choice(USER_AGENTS)
            context = await browser.new_context(
                user_agent=user_agent,
                locale="en-US",
                timezone_id="America/New_York",
                viewport={"width": 1280, "height": 720}
            )
            
            page = await context.new_page()
            
            await page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "DNT": "1"
            })
            
            # Use domcontentloaded instead of networkidle for faster loading
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except:
                # If it still times out, continue with partial page
                pass
            
            # Wait for dynamic content to render
            await page.wait_for_timeout(2000)
            
            if add_delays:
                await apply_human_behavior(page)
            
            page_html = await page.content()
            page_text = await page.evaluate('() => document.body.innerText')
            
            # Extract all links from the page
            links = await page.evaluate('''
                () => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => ({
                            text: a.innerText.trim(),
                            href: a.href,
                            title: a.title || ''
                        }))
                        .filter(link => link.href && link.text)
                        .slice(0, 50)
                }
            ''')
            
            captcha_detected = detect_captcha(page_html + page_text)
            
            content = page_text
            
            if selector:
                try:
                    elements = await page.query_selector_all(selector)
                    contents = []
                    for element in elements:
                        text = await element.inner_text()
                        contents.append(text)
                    content = "\n".join(contents)
                except:
                    content = page_text
            
            await context.close()
            await browser.close()
            
            return {
                "content": content,
                "url": url,
                "links": links,
                "captcha_detected": captcha_detected,
                "user_agent": user_agent,
                "status": "success"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "url": url
        }



@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/routes")
def get_routes():
    return [route.path for route in app.router.routes]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)