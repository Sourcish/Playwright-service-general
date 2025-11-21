# Playwright Deep Crawling & Web Scraping Service

A robust, production-ready web scraping and deep crawling service built with Playwright, FastAPI, and advanced anti-detection techniques.

##  Features

- **Deep Crawling**: Recursive URL discovery and crawling with configurable depth and breadth limits
- **Advanced Stealth**: Browser fingerprinting protection, user-agent rotation, and behavioral mimicry
- **Proxy Support**: Built-in proxy rotation for IP management
- **CAPTCHA Detection**: Automatic CAPTCHA detection with interactive solving support
- **Block Detection**: Intelligent detection of rate limits, IP blocks, and bot challenges
- **Session Management**: Persistent session tracking with success/failure statistics
- **Resource Optimization**: Automatic blocking of unnecessary resources (images, CSS, fonts)
- **Retry Logic**: Exponential backoff and automatic retries on failures
- **Multi-URL Crawling**: Batch processing with configurable delays

##  Prerequisites

- Python 3.8+
- FastAPI
- Playwright
- httpx

##  Installation

### 1. Clone the repository
git clone <your-repo-url>

### 2. Create virtual environment
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

### 3. Install dependencies
pip install -r requirements.txt

# ⚙️ Configuration

### Proxy Configuration
Edit `ProxyConfig.PROXY_POOL` in the code to add your proxy servers:
PROXY_POOL = [
"http://username:password@proxy1.example.com:8080",
"http://username:password@proxy2.example.com:8080",
]

### Docker Execution
docker build . -t "Tag"
docker run -d -p 8080:8080 "image"

### Test locally but checking health
curl localhost:8080/health

### If healthy, deploy it to Cloud run or GKE as per Cloud usage/preference
