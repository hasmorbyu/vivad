"""Provider-agnostic video meeting abstraction.

`Meeting` describes a hearing room; `room_for` returns the join details for the configured
provider. VIVAD never records automatically: recording defaults off and requires explicit,
separately-consented configuration.
"""
from dataclasses import dataclass

from .config import get_settings

PROVIDERS = ("jitsi", "local")


@dataclass
class Meeting:
    provider: str
    room_id: str
    url: str | None
    recording_allowed: bool = False

    def as_dict(self) -> dict:
        return {"provider": self.provider, "room_id": self.room_id, "url": self.url,
                "recording_allowed": self.recording_allowed}


def room_for(case_id: str, hearing_id: int) -> Meeting:
    provider = get_settings().video_provider
    if provider not in PROVIDERS:
        provider = "jitsi"
    room = f"vivad-{case_id}-{hearing_id}".replace(" ", "").lower()
    if provider == "local":
        # Offline fallback: the UI shows a local camera/mic room with no remote peers.
        return Meeting(provider="local", room_id=room, url=None, recording_allowed=False)
    return Meeting(provider="jitsi", room_id=room, url=f"https://meet.jit.si/{room}", recording_allowed=False)
