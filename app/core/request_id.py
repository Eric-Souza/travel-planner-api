import uuid
from contextvars import ContextVar

REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="")


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


def get_request_id() -> str:
    rid = REQUEST_ID_CTX.get()
    return rid or generate_request_id()
