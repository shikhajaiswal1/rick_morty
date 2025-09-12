from fastapi import FastAPI, Query, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from sqlalchemy.exc import OperationalError
from app.db import SessionLocal
from app.models import Character
from app.services import get_filtered_characters

# Initialize FastAPI app
app = FastAPI()

# Initialize the limiter - use IP address as key
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"detail": "Too many requests, please slow down."},
))

# Register middleware
app.add_middleware(SlowAPIMiddleware)

ALLOWED_SORT_FIELDS = ["id", "name"]

@app.get("/characters")
@limiter.limit("10/minute")
def get_characters(request: Request, sort: str = Query("id", description="Sort by field, use '-' for descending")):
    """
    Fetch characters from DB with sorting.
    If DB is empty, data is fetched from Rick & Morty API and saved.
    Rate limit: 10 requests per minute per IP.
    """
    try:
        db = SessionLocal()

        # Check if database is empty
        characters = db.query(Character).all()
        if not characters:
            # Fetch from external API and save to DB
            try:
                get_filtered_characters()
                characters = db.query(Character).all()
            except HTTPException as e:
                raise e
            except Exception:
                raise HTTPException(
                    status_code=503,
                    detail="Failed to fetch data from external API"
                )

        # Sorting logic
        sort_field = sort.lstrip("-")
        order_by = desc if sort.startswith("-") else asc

        if sort_field not in ALLOWED_SORT_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort field. Allowed: {', '.join(ALLOWED_SORT_FIELDS)}"
            )

        sorted_characters = (
            db.query(Character)
            .order_by(order_by(getattr(Character, sort_field)))
            .all()
        )

        db.close()

        return {
            "count": len(sorted_characters),
            "results": [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "species": c.species,
                    "origin": c.origin,
                }
                for c in sorted_characters
            ],
        }

    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Database is not reachable. Please try again later."
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )

@app.get("/healthcheck")
def healthcheck():
    try:
        db = SessionLocal()
        db.execute("SELECT 1")  # simple test query
        db.close()
        return {"status": "healthy"}
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database connection failed")
