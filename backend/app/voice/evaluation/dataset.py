"""Golden Dataset loader for multilingual voice evaluation."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GoldenVoiceEntry:
    audio_id: str
    language: str
    expected_transcript: str
    is_code_switched: bool
    expected_crop: str | None
    expected_disease: str | None
    expected_intent: str
    description: str


class GoldenVoiceDataset:
    """Loads and manages evaluation samples across EN, HI, TE, and code-switched queries."""

    def __init__(self, json_path: Path) -> None:
        self.entries: list[GoldenVoiceEntry] = []
        self._load(json_path)

    def _load(self, json_path: Path) -> None:
        if not json_path.exists():
            raise FileNotFoundError(f"Golden voice dataset file not found at {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            entry = GoldenVoiceEntry(
                audio_id=item["audio_id"],
                language=item["language"],
                expected_transcript=item["expected_transcript"],
                is_code_switched=item.get("is_code_switched", False),
                expected_crop=item.get("expected_crop"),
                expected_disease=item.get("expected_disease"),
                expected_intent=item.get("expected_intent", "CROP_ADVISORY"),
                description=item.get("description", ""),
            )
            self.entries.append(entry)

    def __len__(self) -> int:
        return len(self.entries)
