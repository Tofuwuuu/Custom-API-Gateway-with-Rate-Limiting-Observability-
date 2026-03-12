"""Locations backend - minimal FastAPI app for gateway demo."""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Locations Service", version="0.1.0")


class LocationCreate(BaseModel):
    name: str
    city: str


LOCATIONS_DB: list[dict] = [
    {"id": "1", "name": "Warehouse A", "city": "NYC"},
    {"id": "2", "name": "Warehouse B", "city": "LA"},
]


@app.get("/locations")
def list_locations():
    return {"locations": LOCATIONS_DB}


@app.post("/locations")
def create_location(location: LocationCreate):
    lid = str(len(LOCATIONS_DB) + 1)
    entry = {"id": lid, "name": location.name, "city": location.city}
    LOCATIONS_DB.append(entry)
    return entry


@app.get("/health")
def health():
    return {"status": "ok"}
