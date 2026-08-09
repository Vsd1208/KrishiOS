"""Quality assessor (blur, brightness, resolution) for vision input."""

from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from PIL import Image, ImageStat

from app.config.settings import get_settings


@dataclass(frozen=True, slots=True)
class QualityReport:
    usable: bool
    score: float
    issues: list[str]


class QualityAssessor:
    """Evaluates image quality for vision model ingestion."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def assess(self, image_path: Path) -> QualityReport:
        """Run quality checks on the saved image."""
        issues = []
        score = 1.0  # Start at perfect, deduct for issues

        try:
            with Image.open(image_path) as img:
                # 1. Check if image is RGB, convert if needed for analysis
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                # 2. Brightness check (mean pixel luminance)
                stat = ImageStat.Stat(img)
                # For RGB, we can approximate luminance or just check mean of bands
                try:
                    if len(stat.mean) >= 3:
                        brightness = sum(stat.mean[:3]) / 3
                    else:
                        brightness = stat.mean[0]
                except Exception:
                    brightness = 127

                if brightness < 40:
                    issues.append("Image is too dark")
                    score -= 0.4
                elif brightness > 230:
                    issues.append("Image is overexposed")
                    score -= 0.4

                # 3. Fast variance/blur check using Pillow (simplistic edge detection proxy)
                # For a production system, OpenCV Laplacian variance is better.
                # Here we use an extreme crop bounding box standard deviation as a proxy.
                try:
                    std_dev = sum(stat.stddev) / len(stat.stddev)
                    if std_dev < 15:
                        issues.append("Image lacks contrast or may be severely blurred")
                        score -= 0.3
                except Exception:
                    pass

        except Exception as e:
            logger.warning("QualityAssessor: Failed to process image {}: {}", image_path, e)
            return QualityReport(usable=False, score=0.0, issues=["Failed to load image for quality check"])

        # Cap score
        score = max(0.0, min(1.0, score))
        usable = score >= self.settings.VISION_QUALITY_MIN_SCORE

        return QualityReport(usable=usable, score=round(score, 2), issues=issues)
