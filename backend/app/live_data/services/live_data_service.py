"""Unified Live Agricultural Intelligence Service."""

from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.live_data.providers.base import (
    AdvisoryProvider,
    GovernmentSchemeProvider,
    MarketDataProvider,
    WeatherProvider,
)
from app.live_data.providers.registry import LiveDataProviderRegistry
from app.live_data.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)
from app.live_data.resilience.rate_limiter import TokenBucketRateLimiter
from app.live_data.schemas.advisory import AgriculturalAdvisory
from app.live_data.schemas.common import FreshnessStatus, SourceAuthorityLevel
from app.live_data.schemas.market import MarketPriceObservation
from app.live_data.schemas.scheme import (
    GovernmentScheme,
    SchemeEligibility,
    SchemeEligibilityEvaluation,
)
from app.live_data.schemas.snapshot import DecisionDataSnapshot
from app.live_data.schemas.weather import (
    WeatherAlert,
    WeatherForecast,
    WeatherObservation,
)
from app.live_data.services.cache import LiveDataCacheService
from app.live_data.services.location_resolver import LocationResolver, ResolvedLocation


class LiveDataService:
    """Orchestrates location resolution, circuit breakers, rate limiting, caching, and provider calls."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        registry: LiveDataProviderRegistry | None = None,
        cache_service: LiveDataCacheService | None = None,
        location_resolver: LocationResolver | None = None,
    ) -> None:
        self._session = session
        self._settings = get_settings()
        self._registry = registry or LiveDataProviderRegistry()
        self._cache = cache_service or LiveDataCacheService()
        self._resolver = location_resolver or LocationResolver(session=session)

        # Circuit breakers per domain
        self._cb_weather = CircuitBreaker(
            name="weather_provider",
            failure_threshold=self._settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_time_seconds=self._settings.CIRCUIT_BREAKER_RECOVERY_TIME_SECONDS,
        )
        self._cb_market = CircuitBreaker(
            name="market_provider",
            failure_threshold=self._settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_time_seconds=self._settings.CIRCUIT_BREAKER_RECOVERY_TIME_SECONDS,
        )
        self._cb_advisory = CircuitBreaker(
            name="advisory_provider",
            failure_threshold=self._settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_time_seconds=self._settings.CIRCUIT_BREAKER_RECOVERY_TIME_SECONDS,
        )
        self._cb_scheme = CircuitBreaker(
            name="scheme_provider",
            failure_threshold=self._settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_time_seconds=self._settings.CIRCUIT_BREAKER_RECOVERY_TIME_SECONDS,
        )

        # Rate limiters
        self._rate_limiter = TokenBucketRateLimiter(
            rate_per_minute=self._settings.LIVE_DATA_RATE_LIMIT_PER_MINUTE
        )

    # ── 1. Weather Intelligence ──────────────────────────────────────────────

    async def get_current_weather(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        district: str | None = None,
        state: str | None = None,
        field_id: int | None = None,
        user_uuid: UUID | None = None,
        force_refresh: bool = False,
    ) -> WeatherObservation:
        """Fetch current weather with privacy truncation, caching, and circuit breaker protection."""
        loc = await self._resolver.resolve(
            latitude=latitude,
            longitude=longitude,
            district=district,
            state=state,
            field_id=field_id,
            user_uuid=user_uuid,
        )
        priv_lat, priv_lon = loc.privacy_coords
        cache_params = {"lat": priv_lat, "lon": priv_lon}

        # 1. Cache lookup
        if not force_refresh:
            cached_data = await self._cache.get("weather:current", cache_params)
            if cached_data:
                obs = WeatherObservation.model_validate(cached_data)
                obs.cached = True
                obs.freshness = self._compute_freshness(obs.valid_until)
                return obs

        # 2. Rate limit check
        await self._rate_limiter.wait_and_acquire(1, timeout=1.0)

        # 3. Circuit breaker protected call
        prov = self._registry.get_weather_provider()
        try:
            obs = await self._cb_weather.call(prov.get_current_weather, priv_lat, priv_lon)
            obs.district = loc.district
            obs.state = loc.state
            obs.freshness = FreshnessStatus.FRESH
            obs.cached = False

            # Cache the result
            await self._cache.set(
                "weather:current",
                cache_params,
                obs.model_dump(mode="json"),
                ttl_seconds=self._settings.WEATHER_CACHE_TTL_SECONDS,
            )
            return obs
        except (CircuitBreakerOpenError, Exception) as exc:
            logger.warning("LiveDataService: live weather call failed ({}), attempting fallback", exc)
            # Try serving stale cache if present
            stale_data = await self._cache.get("weather:current", cache_params)
            if stale_data:
                obs = WeatherObservation.model_validate(stale_data)
                obs.freshness = FreshnessStatus.STALE
                obs.cached = True
                return obs

            # Return explicit UNAVAILABLE fallback
            now = datetime.now(UTC)
            return WeatherObservation(
                provider_name=prov.provider_name,
                provider_version=prov.provider_version,
                source="Fallback Offline Weather",
                authority_level=SourceAuthorityLevel.UNVERIFIED_EXTERNAL_SOURCE,
                observed_at=now,
                retrieved_at=now,
                freshness=FreshnessStatus.UNAVAILABLE,
                latitude=loc.latitude,
                longitude=loc.longitude,
                district=loc.district,
                state=loc.state,
                temperature_celsius=27.0,
                relative_humidity_percent=60.0,
                weather_condition="Weather data temporarily unavailable",
            )

    async def get_weather_forecast(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        district: str | None = None,
        state: str | None = None,
        field_id: int | None = None,
        user_uuid: UUID | None = None,
        days: int = 7,
        force_refresh: bool = False,
    ) -> WeatherForecast:
        """Fetch multi-day weather forecast with agricultural spray window intelligence."""
        loc = await self._resolver.resolve(
            latitude=latitude,
            longitude=longitude,
            district=district,
            state=state,
            field_id=field_id,
            user_uuid=user_uuid,
        )
        priv_lat, priv_lon = loc.privacy_coords
        cache_params = {"lat": priv_lat, "lon": priv_lon, "days": days}

        if not force_refresh:
            cached_data = await self._cache.get("weather:forecast", cache_params)
            if cached_data:
                fc = WeatherForecast.model_validate(cached_data)
                fc.cached = True
                fc.freshness = self._compute_freshness(fc.valid_until)
                return fc

        await self._rate_limiter.wait_and_acquire(1, timeout=1.0)
        prov = self._registry.get_weather_provider()
        try:
            fc = await self._cb_weather.call(prov.get_forecast, priv_lat, priv_lon, days=days)
            fc.district = loc.district
            fc.state = loc.state
            fc.freshness = FreshnessStatus.FRESH
            fc.cached = False

            await self._cache.set(
                "weather:forecast",
                cache_params,
                fc.model_dump(mode="json"),
                ttl_seconds=self._settings.WEATHER_FORECAST_CACHE_TTL_SECONDS,
            )
            return fc
        except Exception as exc:
            logger.warning("LiveDataService: weather forecast failed ({})", exc)
            now = datetime.now(UTC)
            return WeatherForecast(
                provider_name=prov.provider_name,
                provider_version=prov.provider_version,
                source="Fallback Weather Forecast",
                authority_level=SourceAuthorityLevel.UNVERIFIED_EXTERNAL_SOURCE,
                observed_at=now,
                retrieved_at=now,
                freshness=FreshnessStatus.UNAVAILABLE,
                latitude=loc.latitude,
                longitude=loc.longitude,
                district=loc.district,
                state=loc.state,
                forecast_days=[],
                summary="Forecast temporarily unavailable. Check local IMD bulletin.",
                spray_window_favorable=False,
                spray_window_reason="Forecast unavailable to confirm spray safety.",
            )

    async def get_weather_alerts(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        user_uuid: UUID | None = None,
    ) -> list[WeatherAlert]:
        loc = await self._resolver.resolve(latitude=latitude, longitude=longitude, user_uuid=user_uuid)
        priv_lat, priv_lon = loc.privacy_coords
        prov = self._registry.get_weather_provider()
        try:
            return await self._cb_weather.call(prov.get_alerts, priv_lat, priv_lon)
        except Exception:
            return []

    # ── 2. Market / Mandi Intelligence ───────────────────────────────────────

    async def get_market_prices(
        self,
        commodity: str,
        state: str | None = None,
        district: str | None = None,
        user_uuid: UUID | None = None,
        force_refresh: bool = False,
    ) -> list[MarketPriceObservation]:
        """Fetch commodity market mandi prices and MSP benchmarks."""
        loc = await self._resolver.resolve(district=district, state=state, user_uuid=user_uuid)
        cache_params = {"commodity": commodity.lower(), "state": loc.state, "district": loc.district}

        if not force_refresh:
            cached_data = await self._cache.get("market:mandi", cache_params)
            if cached_data and "items" in cached_data:
                items = [MarketPriceObservation.model_validate(x) for x in cached_data["items"]]
                for item in items:
                    item.cached = True
                    item.freshness = self._compute_freshness(item.valid_until)
                return items

        await self._rate_limiter.wait_and_acquire(1, timeout=1.0)
        prov = self._registry.get_market_provider()
        try:
            prices = await self._cb_market.call(
                prov.get_commodity_prices,
                commodity=commodity,
                state=loc.state,
                district=loc.district,
            )
            for p in prices:
                p.freshness = FreshnessStatus.FRESH
                p.cached = False

            await self._cache.set(
                "market:mandi",
                cache_params,
                {"items": [p.model_dump(mode="json") for p in prices]},
                ttl_seconds=self._settings.MARKET_CACHE_TTL_SECONDS,
            )
            return prices
        except Exception as exc:
            logger.warning("LiveDataService: market prices failed ({})", exc)
            return []

    # ── 3. Agricultural Advisories ───────────────────────────────────────────

    async def get_advisories(
        self,
        crop: str,
        state: str | None = None,
        district: str | None = None,
        user_uuid: UUID | None = None,
        force_refresh: bool = False,
    ) -> list[AgriculturalAdvisory]:
        """Fetch active agricultural advisories for crop and location."""
        loc = await self._resolver.resolve(district=district, state=state, user_uuid=user_uuid)
        cache_params = {"crop": crop.lower(), "state": loc.state, "district": loc.district}

        if not force_refresh:
            cached_data = await self._cache.get("advisory:list", cache_params)
            if cached_data and "items" in cached_data:
                items = [AgriculturalAdvisory.model_validate(x) for x in cached_data["items"]]
                for item in items:
                    item.cached = True
                    item.freshness = self._compute_freshness(item.valid_until)
                return items

        await self._rate_limiter.wait_and_acquire(1, timeout=1.0)
        prov = self._registry.get_advisory_provider()
        try:
            advisories = await self._cb_advisory.call(
                prov.get_advisories,
                crop=crop,
                state=loc.state,
                district=loc.district,
            )
            for a in advisories:
                a.freshness = FreshnessStatus.FRESH
                a.cached = False

            await self._cache.set(
                "advisory:list",
                cache_params,
                {"items": [a.model_dump(mode="json") for a in advisories]},
                ttl_seconds=self._settings.ADVISORY_CACHE_TTL_SECONDS,
            )
            return advisories
        except Exception as exc:
            logger.warning("LiveDataService: advisory fetch failed ({})", exc)
            return []

    # ── 4. Government Welfare Schemes ────────────────────────────────────────

    async def get_government_schemes(
        self,
        state: str | None = None,
        crop: str | None = None,
        farmer_category: str | None = None,
        user_uuid: UUID | None = None,
    ) -> list[GovernmentScheme]:
        """Fetch government schemes matching farmer profile and state context."""
        loc = await self._resolver.resolve(state=state, user_uuid=user_uuid)
        prov = self._registry.get_scheme_provider()
        try:
            return await self._cb_scheme.call(
                prov.get_schemes,
                state=loc.state,
                crop=crop,
                farmer_category=farmer_category,
            )
        except Exception as exc:
            logger.warning("LiveDataService: scheme fetch failed ({})", exc)
            return []

    async def evaluate_scheme_eligibility(
        self,
        scheme_id: str,
        landholding_acres: float | None = None,
        crop: str | None = None,
        state: str | None = None,
        farmer_category: str | None = None,
    ) -> SchemeEligibilityEvaluation:
        """Strictly evaluate scheme eligibility without hallucination or fabrication."""
        prov = self._registry.get_scheme_provider()
        scheme = await prov.get_scheme_by_id(scheme_id)
        if not scheme:
            raise ValueError(f"Scheme with ID '{scheme_id}' not found.")

        missing: list[str] = []
        if landholding_acres is None and scheme.max_landholding_acres is not None:
            missing.append("landholding_acres")
        if state is None and scheme.state is not None:
            missing.append("state")

        # If required criteria missing, return UNKNOWN
        if missing:
            return SchemeEligibilityEvaluation(
                scheme=scheme,
                eligibility=SchemeEligibility.UNKNOWN,
                reason=f"Eligibility cannot be determined because required profile data ({', '.join(missing)}) is unavailable.",
                missing_criteria=missing,
            )

        # Check state match
        if scheme.state and state and scheme.state.lower() != state.lower():
            return SchemeEligibilityEvaluation(
                scheme=scheme,
                eligibility=SchemeEligibility.NOT_ELIGIBLE,
                reason=f"Scheme applies only to {scheme.state}, but user is in {state}.",
            )

        # Check landholding
        if scheme.max_landholding_acres and landholding_acres and landholding_acres > scheme.max_landholding_acres:
            return SchemeEligibilityEvaluation(
                scheme=scheme,
                eligibility=SchemeEligibility.NOT_ELIGIBLE,
                reason=f"Landholding of {landholding_acres} acres exceeds maximum limit of {scheme.max_landholding_acres} acres.",
            )

        # Check crop match
        if crop and scheme.target_crops:
            if not any(c.lower() in [crop.lower(), "all crops"] for c in scheme.target_crops):
                return SchemeEligibilityEvaluation(
                    scheme=scheme,
                    eligibility=SchemeEligibility.NOT_ELIGIBLE,
                    reason=f"Crop '{crop}' is not covered under scheme target crops ({', '.join(scheme.target_crops)}).",
                )

        return SchemeEligibilityEvaluation(
            scheme=scheme,
            eligibility=SchemeEligibility.ELIGIBLE,
            reason="Farmer satisfies all verified criteria for this scheme.",
        )

    # ── 5. Decision Data Snapshot Creation ───────────────────────────────────

    def create_snapshot(
        self,
        execution_id: UUID,
        user_uuid: UUID,
        field_id: int | None = None,
        weather: WeatherObservation | None = None,
        market: MarketPriceObservation | None = None,
        advisory: AgriculturalAdvisory | None = None,
    ) -> DecisionDataSnapshot:
        """Create an immutable snapshot of all live data telemetry used in an advisory decision."""
        return DecisionDataSnapshot(
            execution_id=execution_id,
            user_uuid=user_uuid,
            field_id=field_id,
            weather_response_id=weather.response_id if weather else None,
            weather_observed_at=weather.observed_at if weather else None,
            weather_freshness=weather.freshness.value if weather else None,
            market_response_id=market.response_id if market else None,
            market_modal_price=market.modal_price_inr_quintal if market else None,
            market_freshness=market.freshness.value if market else None,
            advisory_id=advisory.advisory_id if advisory else None,
            advisory_authority=advisory.issuing_authority if advisory else None,
        )

    # ── Helper ───────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_freshness(valid_until: datetime | None) -> FreshnessStatus:
        if valid_until is None:
            return FreshnessStatus.FRESH
        now = datetime.now(UTC)
        if now > valid_until:
            return FreshnessStatus.EXPIRED
        return FreshnessStatus.FRESH
