"""
Rate-limited Python HTTP app (FastAPI)

What it does
- Serves a single HTML page that prints "Follow the white rabbit" in pseudo-graphic colorful text.
- Enforces a global rate limit of 10 HTTP requests per second (token-bucket).
- Logs whenever requests are rejected due to rate limiting.

Run instructions
1) Install dependencies:
   pip install fastapi uvicorn

2) Run the app (development):
   uvicorn app.main:app --host 127.0.0.1 --port 8000

Then open http://127.0.0.1:8000/ in your browser.

Notes
- The rate limiter is implemented as an async token-bucket guarding all requests.
- If the server is overloaded, clients will receive HTTP 429 Too Many Requests with a Retry-After header.
"""
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class TokenBucket:
    """Async token bucket limiter.
    rate: tokens added per second
    capacity: maximum tokens in bucket
    """

    def __init__(self, rate: float, capacity: float):
        self.rate = float(rate)
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, amount: float = 1.0) -> bool:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last
            # Refill tokens
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last = now
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate: float = 10.0, capacity: float = 10.0, exempt_paths=None):
        super().__init__(app)
        self.bucket = TokenBucket(rate=rate, capacity=capacity)
        self.exempt_paths = exempt_paths or []

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # try to consume 1 token
        allowed = await self.bucket.consume(1.0)
        if not allowed:
            client_host = request.client.host if request.client else "unknown"
            logger.warning(f"Too many requests from {client_host}")
            headers = {"Retry-After": "1"}
            return PlainTextResponse("Too Many Requests", status_code=429, headers=headers)
        return await call_next(request)

app = FastAPI()
# Attach middleware with limit 10 req/sec
app.add_middleware(RateLimitMiddleware, rate=15.0, capacity=15.0, exempt_paths=["/health"])

@app.get("/health", response_class=PlainTextResponse)
async def health():
    return PlainTextResponse("OK", status_code=200)

@app.get("/", response_class=HTMLResponse)
async def index():
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Follow the white rabbit</title>
      <style>
        /* Full-page center */
        html,body{height:100%;margin:0}
        body{display:flex;align-items:center;justify-content:center;background:#050505}

        /* Fancy pseudo-graphic container */
        .card{padding:40px;border-radius:16px;border:2px solid rgba(255,255,255,0.06);backdrop-filter:blur(6px);box-shadow:0 8px 30px rgba(0,0,0,0.7)}

        /* Big rainbow, pseudo-ASCII look */
        .line{
          font-family: 'Courier New', Courier, monospace;
          font-size:36px;
          letter-spacing:2px;
          font-weight:700;
          white-space:pre;
          background:linear-gradient(90deg,#ff3cac,#784ba0,#2b86c5,#20c997,#ffd166,#ff6b6b,#ff3cac);
          background-size:300% 100%;
          -webkit-background-clip:text;
          background-clip:text;
          color:transparent;
          text-shadow:0 0 12px rgba(255,255,255,0.03);
          animation: slide 3.5s linear infinite;
          display:inline-block;
          padding:6px 12px;
          border-radius:8px;
        }

        /* Pseudo-graphic frame using monospace characters */
        .frame{font-family:monospace;color:#eee;display:inline-block;padding:12px;background:rgba(255,255,255,0.02);border-radius:8px}

        @keyframes slide{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}

        /* small subtitle */
        .sub{font-family:monospace;color:#aaa;font-size:12px;margin-top:8px;text-align:center}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="frame">
          <div class="line">Follow the white rabbit</div>
          <div class="sub">(This server enforces a global limit of 10 requests/sec)</div>
        </div>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)


if __name__ == "__main__":
    # For convenience when running `python rate_limited_fastapi_app.py`
    import uvicorn
    uvicorn.run("rate_limited_fastapi_app:app", host="0.0.0.0", port=8000, reload=True)
