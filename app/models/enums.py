import enum


class TripStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class BookingStatus(str, enum.Enum):
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CONFLICT = "conflict"


class BookingType(str, enum.Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    TRAIN = "train"
    BUS = "bus"
    RESTAURANT = "restaurant"
    ACTIVITY = "activity"
    OTHER = "other"


class DocumentProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    HOTEL_RESERVATION = "hotel_reservation"
    FLIGHT_TICKET = "flight_ticket"
    TRAIN_TICKET = "train_ticket"
    BUS_TICKET = "bus_ticket"
    ACTIVITY_BOOKING = "activity_booking"
    RESTAURANT_RESERVATION = "restaurant_reservation"
    TRAVEL_NOTE = "travel_note"
    UNKNOWN = "unknown"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProposalStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"


class ItineraryItemStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    SUGGESTED = "suggested"
    LOCKED = "locked"
