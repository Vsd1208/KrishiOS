"""NLU result contracts (frozen dataclasses, shared by all NLU providers)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Intent(StrEnum):
    ADVISORY = "advisory"
    DISEASE = "disease"
    WEATHER = "weather"
    MARKET = "market"
    SCHEME = "scheme"
    GOVT_BULLETIN = "govt_bulletin"
    YIELD = "yield"
    OFFICER = "officer"
    SMALLTALK = "smalltalk"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True, slots=True)
class NLUEntities:
    """Entities resolved against the crop catalog and LGD (never free strings)."""

    crop: str | None = None
    crop_status: str = "not_found"  # resolved | ambiguous | multiple | not_found
    crop_candidates: tuple[str, ...] = ()
    district_lgd_code: int | None = None
    district_name: str | None = None
    district_candidates: tuple[int, ...] = ()
    season: str | None = None
    symptoms: tuple[str, ...] = ()
    time_expression: str | None = None
    scheme: str | None = None


@dataclass(frozen=True, slots=True)
class NLUResult:
    intent: Intent
    confidence: float
    language: str  # en | hi | te
    is_code_switched: bool
    entities: NLUEntities
    secondary_intents: tuple[Intent, ...] = ()
    script: str = "latin"
    romanized: bool = False
    provider: str = "rule-based-nlu"
    provider_version: str = ""
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["intent"] = self.intent.value
        data["secondary_intents"] = [i.value for i in self.secondary_intents]
        return data
