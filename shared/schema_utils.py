from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CallManifestEntry:
    call_id: str
    lead_number: str
    recording_url: str
    audio_path: str
    duration: Any
    owner: str
    campaign: str
    walkin_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PhaseOutputEntry:
    call_id: str
    source_path: str
    output_path: str
    metadata_path: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(payload.pop("extra"))
        return payload

