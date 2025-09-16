# app/services.py
import requests
import time
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.db import SessionLocal
from app.models import Character

BASE_URL = "https://rickandmortyapi.com/api/character"


def get_filtered_characters():
    db = SessionLocal()
    results = []
    page = 1

    while True:
        try:
            response = requests.get(f"{BASE_URL}?page={page}", timeout=5)
        except requests.exceptions.RequestException:
            raise HTTPException(
                status_code=503, detail="Failed to connect to external API"
            )

        # Handle rate limiting (HTTP 429)
        if response.status_code == 429:
            time.sleep(2)  # wait before retrying
            continue

        # Handle other non-success codes
        if response.status_code != 200:
            raise HTTPException(
                status_code=503, detail="External API returned an error"
            )

        data = response.json()
        for char in data.get("results", []):
            if (
                char["species"] == "Human"
                and char["status"] == "Alive"
                and "Earth" in char["origin"]["name"]
            ):
                # Save to DB
                character_obj = Character(
                    id=char["id"],
                    name=char["name"],
                    status=char["status"],
                    species=char["species"],
                    origin=char["origin"]["name"],
                )

                try:
                    db.add(character_obj)
                    db.commit()
                except IntegrityError:
                    db.rollback()  # Skip duplicates

                results.append(
                    {
                        "id": char["id"],
                        "name": char["name"],
                        "origin": char["origin"]["name"],
                        "status": char["status"],
                    }
                )

        if data["info"]["next"] is None:
            break
        page += 1

    db.close()
    return results
