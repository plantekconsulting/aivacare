"""In-process event bus feeding Server-Sent Events to dashboards and patient apps."""
import asyncio
import json
from dataclasses import dataclass, field


@dataclass(eq=False)
class Subscriber:
    role: str
    sub: str
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=100))


_subscribers: set[Subscriber] = set()


def subscribe(role: str, sub: str) -> Subscriber:
    s = Subscriber(role, sub)
    _subscribers.add(s)
    return s


def unsubscribe(s: Subscriber) -> None:
    _subscribers.discard(s)


def publish(event: str, data: dict, *, patient_id: str | None = None, clinicians: bool = False) -> None:
    """Deliver to clinicians/admins (if clinicians=True) and/or the patient themselves."""
    msg = json.dumps({"event": event, "data": data}, default=str)
    for s in list(_subscribers):
        wanted = (clinicians and s.role in {"clinician", "admin"}) or (patient_id and s.sub == patient_id)
        if wanted:
            try:
                s.queue.put_nowait(msg)
            except asyncio.QueueFull:
                pass
