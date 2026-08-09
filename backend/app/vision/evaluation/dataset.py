"""Dataset loader for the golden vision evaluation set."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GoldenEntry:
    image_id: str
    crop: str
    ground_truth_condition: str
    expected_entities: list[str]
    description: str


class GoldenDataset:
    """Loads and manages the golden dataset for vision evaluation."""

    def __init__(self, json_path: Path) -> None:
        self.entries: list[GoldenEntry] = []
        self._load(json_path)

    def _load(self, json_path: Path) -> None:
        if not json_path.exists():
            raise FileNotFoundError(f"Golden dataset not found at {json_path}")
            
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for item in data:
            entry = GoldenEntry(
                image_id=item["image_id"],
                crop=item["crop"],
                ground_truth_condition=item["ground_truth_condition"],
                expected_entities=item.get("expected_entities", []),
                description=item.get("description", ""),
            )
            self.entries.append(entry)

    def __len__(self) -> int:
        return len(self.entries)
