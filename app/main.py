from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse # <-- Use FastAPI's JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from sqlalchemy.exc import OperationalError

# Import SlowAPI
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Local imports
from app.db import SessionLocal
from app.db import Base, engine
from app.models import Character
from app.services import get_filtered_characters

#Setup Cache
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from fastapi import Depends

#sqlalchemy.text() wrapper
from sqlalchemy import text

# Initialize FastAPI app
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # For dev: in-memory cache (resets on restart)
    FastAPICache.init(InMemoryBackend(), prefix="rickmorty-cache")

# --- Auto-create DB tables ---
def on_startup():
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)

# Rate limiter setup (based on client IP)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# -------------------------------
# Rate limit handler (headers + JSON)
# -------------------------------
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests, please slow down."},
        headers={
            "X-RateLimit-Limit": str(exc.limit.limit),           # total allowed requests
            "X-RateLimit-Remaining": str(exc.limit.remaining),   # remaining requests
            "X-RateLimit-Reset": str(int(exc.reset_in_seconds)), # seconds until reset
            "Retry-After": str(int(exc.reset_in_seconds))        # retry after seconds
        }
    )

# Register handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Constants
ALLOWED_SORT_FIELDS = ["id", "name"]


# -------------------------------
# Endpoints
# -------------------------------
@app.get("/characters")
@limiter.limit("10/minute")
@cache(expire=60)  # Cache results for 60 seconds
def get_characters(
        request: Request,
        sort: str = Query("id", description="Sort by field, use '-' for descending"),
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Results per page"),
        name: str | None = Query(None, description="Filter by character name (partial match)"),
        status: str | None = Query(None, description="Filter by status: Alive, Dead, unknown"),
        species: str | None = Query(None, description="Filter by species"),
        origin: str | None = Query(None, description="Filter by origin (partial match)")
):
    """
    Fetch characters with filtering, sorting, pagination, and caching.
    """
    try:
        db = SessionLocal()

        # Ensure DB has data
        characters = db.query(Character).all()
        if not characters:
            get_filtered_characters()
            characters = db.query(Character).all()

        # Sorting setup
        sort_field = sort.lstrip("-")
        order_by = desc if sort.startswith("-") else asc
        if sort_field not in ALLOWED_SORT_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort field. Allowed: {', '.join(ALLOWED_SORT_FIELDS)}"
            )

        # Base query
        query = db.query(Character)

        # Apply filters
        if name:
            query = query.filter(Character.name.ilike(f"%{name}%"))  # case-insensitive partial match
        if status:
            query = query.filter(Character.status == status)
        if species:
            query = query.filter(Character.species == species)
        if origin:
            query = query.filter(Character.origin.ilike(f"%{origin}%"))

        # Count results
        total = query.count()

        # Apply sorting + pagination
        items = (
            query.order_by(order_by(getattr(Character, sort_field)))
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        db.close()

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
            "results": [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "species": c.species,
                    "origin": c.origin,
                }
                for c in items
            ],
        }

    except OperationalError:
        raise HTTPException(status_code=503, detail="Database not reachable")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error occurred")
@app.get("/healthcheck")
def healthcheck():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))  # simple test query
        db.close()
        return {"status": "healthy"}
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database connection failed")
