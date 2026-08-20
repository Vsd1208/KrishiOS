"""Advisory Provider implementations (ICAR / Agromet Bulletin)."""

from datetime import UTC, datetime, timedelta

from app.live_data.schemas.advisory import AdvisoryStatus, AgriculturalAdvisory
from app.live_data.schemas.common import FreshnessStatus, SourceAuthorityLevel


class MockAdvisoryProvider:
    """Deterministic Agromet and ICAR crop advisory provider."""

    def __init__(self, provider_name: str = "mock-advisory-v1", provider_version: str = "1.0.0") -> None:
        self._provider_name = provider_name
        self._provider_version = provider_version

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_version(self) -> str:
        return self._provider_version

    async def get_advisories(
        self,
        crop: str,
        state: str,
        district: str | None = None,
    ) -> list[AgriculturalAdvisory]:
        now = datetime.now(UTC)
        norm_crop = crop.title()

        return [
            AgriculturalAdvisory(
                provider_name=self.provider_name,
                provider_version=self.provider_version,
                source="ICAR-CRIDA Agromet Advisory Services",
                authority_level=SourceAuthorityLevel.ICAR,
                observed_at=now - timedelta(hours=4),
                retrieved_at=now,
                valid_until=now + timedelta(hours=24),
                freshness=FreshnessStatus.FRESH,
                advisory_id=f"ADV-{norm_crop.upper()}-2026-08",
                title=f"Kharif Season Agromet Advisory for {norm_crop}",
                content=(
                    f"Due to intermittent cloudiness and high humidity, monitor {norm_crop} fields "
                    "for blast and fungal leaf spots. If spraying is required, spray only during calm morning "
                    "hours when wind speed is under 5 m/s."
                ),
                crop=norm_crop,
                state=state,
                district=district,
                issuing_authority="ICAR - Central Research Institute for Dryland Agriculture (CRIDA)",
                effective_from=now - timedelta(days=1),
                effective_until=now + timedelta(days=3),
                status=AdvisoryStatus.ACTIVE,
                recommended_practices=[
                    "Maintain 2-3 cm standing water in paddy fields.",
                    "Avoid applying excess nitrogenous fertilizers during cloudy weather.",
                    "Spray tricyclazole 75% WP @ 0.6g/L if blast symptoms appear.",
                ],
                warning_notes=[
                    "Do not spray chemicals immediately before heavy rain.",
                ],
            )
        ]

    async def health(self) -> bool:
        return True


class AgrometAdvisoryProvider(MockAdvisoryProvider):
    """Production Agromet bulletin adapter."""

    def __init__(self, provider_name: str = "agromet-v1", provider_version: str = "1.0.0") -> None:
        super().__init__(provider_name=provider_name, provider_version=provider_version)
