import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.db.database import init_db
from app.routers import ip_addresses, prefixes, reset, roles

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ipam")

# ---------------------------------------------------------------------------
# Database init
# ---------------------------------------------------------------------------
init_db()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="IPAM",
    description="NetBox-compatible IPAM REST API",
    version="0.1.0",
)

IPAM_PREFIX = "/api/ipam"
RESET_PREFIX = "/api"

app.include_router(prefixes.router, prefix=IPAM_PREFIX)
app.include_router(ip_addresses.router, prefix=IPAM_PREFIX)
app.include_router(roles.router, prefix=IPAM_PREFIX)
app.include_router(reset.router, prefix=RESET_PREFIX)


@app.get("/api/ipam/", include_in_schema=False)
def ipam_root(request: Request):
    base = str(request.base_url).rstrip("/")
    return JSONResponse({
        "roles": f"{base}/api/ipam/roles/",
        "ip-addresses": f"{base}/api/ipam/ip-addresses/",
        "prefixes": f"{base}/api/ipam/prefixes/",
    })


@app.get("/api/status/", include_in_schema=False)
def status():
    return JSONResponse({"netbox-version": "Simpam 67"})


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def serve_ui():
    with open("app/static/index.html") as f:
        return HTMLResponse(content=f.read())


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response
