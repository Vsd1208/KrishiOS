"""Government Scheme Provider implementations (PM-KISAN, PMFBY, Rythu Bandhu/Bharosa)."""

from datetime import UTC, datetime, timedelta

from app.live_data.schemas.common import FreshnessStatus, SourceAuthorityLevel
from app.live_data.schemas.scheme import GovernmentScheme


class MockGovernmentSchemeProvider:
    """Deterministic Government welfare and subsidy database provider."""

    def __init__(self, provider_name: str = "mock-scheme-v1", provider_version: str = "1.0.0") -> None:
        self._provider_name = provider_name
        self._provider_version = provider_version

        # Preloaded verified Central & State schemes
        self._schemes: list[GovernmentScheme] = [
            GovernmentScheme(
                provider_name=self._provider_name,
                provider_version=self._provider_version,
                source="Ministry of Agriculture & Farmers Welfare, GoI",
                authority_level=SourceAuthorityLevel.GOVERNMENT,
                observed_at=datetime.now(UTC),
                retrieved_at=datetime.now(UTC),
                valid_until=datetime.now(UTC) + timedelta(days=90),
                freshness=FreshnessStatus.FRESH,
                scheme_id="GOI-PM-KISAN",
                name="Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
                description="Direct income support of ₹6,000 per year in 3 equal installments to all landholding farmer families.",
                state=None,  # Central
                target_crops=["Paddy", "Cotton", "Wheat", "Maize", "All Crops"],
                max_landholding_acres=None,  # All landholding farmers eligible
                farmer_categories=["Small", "Marginal", "Medium", "Large"],
                benefits="₹6,000 per annum credited directly to Aadhaar-seeded bank accounts in 3 tranches of ₹2,000.",
                subsidy_amount_or_percent="100% Direct Cash Transfer",
                application_process="Apply online at pmkisan.gov.in or through Common Service Centers (CSC) with Aadhaar and land passbook.",
                official_portal_url="https://pmkisan.gov.in",
                last_verified_at=datetime.now(UTC),
                status="Active",
            ),
            GovernmentScheme(
                provider_name=self._provider_name,
                provider_version=self._provider_version,
                source="Ministry of Agriculture & Farmers Welfare, GoI",
                authority_level=SourceAuthorityLevel.GOVERNMENT,
                observed_at=datetime.now(UTC),
                retrieved_at=datetime.now(UTC),
                valid_until=datetime.now(UTC) + timedelta(days=90),
                freshness=FreshnessStatus.FRESH,
                scheme_id="GOI-PMFBY",
                name="Pradhan Mantri Fasal Bima Yojana (PMFBY)",
                description="Comprehensive crop insurance against non-preventable natural risks from pre-sowing to post-harvest.",
                state=None,
                target_crops=["Paddy", "Cotton", "Wheat", "Maize", "Pulses", "Oilseeds"],
                max_landholding_acres=None,
                farmer_categories=["Small", "Marginal", "Tenant", "Sharecroppers"],
                benefits="Subsidized premium: 2.0% for Kharif food/oilseeds crops, 1.5% for Rabi crops, 5% for commercial/horticultural crops.",
                subsidy_amount_or_percent="Up to 90% premium subsidy shared by Central & State Govts",
                application_process="Apply via National Crop Insurance Portal (pmfby.gov.in) or designated banks within cut-off dates.",
                official_portal_url="https://pmfby.gov.in",
                last_verified_at=datetime.now(UTC),
                status="Active",
            ),
            GovernmentScheme(
                provider_name=self._provider_name,
                provider_version=self._provider_version,
                source="Department of Agriculture, Govt of Telangana",
                authority_level=SourceAuthorityLevel.GOVERNMENT,
                observed_at=datetime.now(UTC),
                retrieved_at=datetime.now(UTC),
                valid_until=datetime.now(UTC) + timedelta(days=90),
                freshness=FreshnessStatus.FRESH,
                scheme_id="TS-RYTHU-BHAROSA",
                name="Telangana Rythu Bharosa Investment Support",
                description="Financial assistance of ₹15,000 per acre per year for agricultural inputs.",
                state="Telangana",
                target_crops=["Paddy", "Cotton", "Chilli", "Maize", "All Crops"],
                max_landholding_acres=10.0,
                farmer_categories=["Small", "Marginal", "Tenant"],
                benefits="Direct financial investment support for seeds, fertilizers, and land preparation.",
                subsidy_amount_or_percent="₹15,000 per acre/year",
                application_process="Enrolled automatically via Dharani portal land record verification.",
                official_portal_url="https://rythubandhu.telangana.gov.in",
                last_verified_at=datetime.now(UTC),
                status="Active",
            ),
        ]

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_version(self) -> str:
        return self._provider_version

    async def get_schemes(
        self,
        state: str | None = None,
        crop: str | None = None,
        farmer_category: str | None = None,
    ) -> list[GovernmentScheme]:
        results: list[GovernmentScheme] = []
        for s in self._schemes:
            # Check state match: central scheme (state=None) or exact state match
            if state and s.state and s.state.lower() != state.lower():
                continue
            # Check crop match
            if crop and s.target_crops:
                if not any(c.lower() in [crop.lower(), "all crops"] for c in s.target_crops):
                    continue
            # Check farmer category match
            if farmer_category and s.farmer_categories:
                if not any(fc.lower() == farmer_category.lower() for fc in s.farmer_categories):
                    continue
            results.append(s)
        return results

    async def get_scheme_by_id(self, scheme_id: str) -> GovernmentScheme | None:
        for s in self._schemes:
            if s.scheme_id == scheme_id:
                return s
        return None

    async def health(self) -> bool:
        return True
