"""Evaluation fixtures for extraction, retrieval, and planner validation."""

EXTRACTION_CASES = [
    {
        "name": "hotel_reservation",
        "text": "Hotel Palermo\nCheck-in: Aug 5 2026 15:00\nConfirmation: HTL123",
        "expected_fields": ["title", "confirmation_code", "start_at"],
    },
    {
        "name": "ambiguous_email",
        "text": "Your trip details may arrive later.",
        "expect_uncertainty": True,
    },
]

RAG_CASES = [
    {"question": "What time is check-in?", "must_contain": ["15:00", "check"]},
    {"question": "What is the cancellation policy?", "must_cite": True},
    {"question": "Does the document mention airport transfer?", "allow_not_found": True},
]

PLANNER_CASES = [
    {"rule": "no_overlap_confirmed_flight", "locked": True},
    {"rule": "rainy_day_preserves_locked", "mode": "rainy_day"},
]
