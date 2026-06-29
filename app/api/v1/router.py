from fastapi import APIRouter

from app.api.v1.routes import (
    bookings,
    chat,
    documents,
    eval,
    health,
    itinerary,
    places,
    preferences,
    retrieval,
    trips,
)

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health.router)
v1_router.include_router(trips.router)
v1_router.include_router(preferences.router)
v1_router.include_router(bookings.router)
v1_router.include_router(documents.router)
v1_router.include_router(retrieval.router)
v1_router.include_router(chat.router)
v1_router.include_router(itinerary.router)
v1_router.include_router(places.router)
v1_router.include_router(eval.router)
