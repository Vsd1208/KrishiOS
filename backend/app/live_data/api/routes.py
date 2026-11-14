"""REST API routes for Live Agricultural Intelligence."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission, get_current_auth_context
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.live_data.schemas.advisory import AgriculturalAdvisory
from app.live_data.schemas.market import MarketPriceObservation
from app.live_data.schemas.scheme import GovernmentScheme, SchemeEligibilityEvaluation
from app.live_data.schemas.weather import WeatherAlert, WeatherForecast, WeatherObservation
from app.live_data.services.live_data_service import LiveDataService

router = APIRouter(prefix="/live", tags=["Live Agricultural Intelligence"])


@router.get(
    "/weather/current",
    response_model=WeatherObservation,
    dependencies=[Depends(RequirePermission(Permission.WEATHER_READ))],
)
async def get_current_weather(
    latitude: float | None = Query(None, description="Latitude"),
    longitude: float | None = Query(None, description="Longitude"),
    district: str | None = Query(None, description="District name"),
    state: str | None = Query(None, description="State name"),
    field_id: int | None = Query(None, description="Field ID"),
    force_refresh: bool = Query(False, description="Bypass cache"),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> WeatherObservation:
    """Retrieve verified real-time weather observation for coordinates, field, or farmer location."""
    service = LiveDataService(session=session)
    return await service.get_current_weather(
        latitude=latitude,
        longitude=longitude,
        district=district,
        state=state,
        field_id=field_id,
        user_uuid=auth.user_uuid,
        force_refresh=force_refresh,
    )


@router.get(
    "/weather/forecast",
    response_model=WeatherForecast,
    dependencies=[Depends(RequirePermission(Permission.WEATHER_READ))],
)
async def get_weather_forecast(
    latitude: float | None = Query(None, description="Latitude"),
    longitude: float | None = Query(None, description="Longitude"),
    district: str | None = Query(None, description="District name"),
    state: str | None = Query(None, description="State name"),
    field_id: int | None = Query(None, description="Field ID"),
    days: int = Query(7, ge=1, le=14, description="Forecast days"),
    force_refresh: bool = Query(False, description="Bypass cache"),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> WeatherForecast:
    """Retrieve multi-day agricultural weather forecast with spray window advisory."""
    service = LiveDataService(session=session)
    return await service.get_weather_forecast(
        latitude=latitude,
        longitude=longitude,
        district=district,
        state=state,
        field_id=field_id,
        user_uuid=auth.user_uuid,
        days=days,
        force_refresh=force_refresh,
    )


@router.get(
    "/weather/alerts",
    response_model=list[WeatherAlert],
    dependencies=[Depends(RequirePermission(Permission.WEATHER_READ))],
)
async def get_weather_alerts(
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> list[WeatherAlert]:
    """Retrieve active severe meteorological warnings."""
    service = LiveDataService(session=session)
    return await service.get_weather_alerts(
        latitude=latitude,
        longitude=longitude,
        user_uuid=auth.user_uuid,
    )


@router.get(
    "/market/prices",
    response_model=list[MarketPriceObservation],
    dependencies=[Depends(RequirePermission(Permission.MARKET_READ))],
)
async def get_market_prices(
    commodity: str = Query(..., description="Crop commodity name (e.g. Paddy, Cotton)"),
    state: str | None = Query(None, description="State name"),
    district: str | None = Query(None, description="District name"),
    force_refresh: bool = Query(False, description="Bypass cache"),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> list[MarketPriceObservation]:
    """Retrieve commodity mandi arrivals, modal prices (₹/quintal), and MSP benchmarks."""
    service = LiveDataService(session=session)
    return await service.get_market_prices(
        commodity=commodity,
        state=state,
        district=district,
        user_uuid=auth.user_uuid,
        force_refresh=force_refresh,
    )


@router.get(
    "/market/trend",
    dependencies=[Depends(RequirePermission(Permission.MARKET_READ))],
)
async def get_market_trend(
    commodity: str = Query(..., description="Crop name (any catalog alias, e.g. Cotton, Paddy)"),
    district: str = Query(..., description="District name as published by AGMARKNET"),
    days: int = Query(30, ge=7, le=180),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Daily median modal price across the district's mandis (official AGMARKNET history),
    with the 7-day change. Empty when no history has been stored yet."""
    from app.live_data.market_history import crop_key, trend  # noqa: PLC0415
    from app.live_data.providers.market_provider import official_msp  # noqa: PLC0415

    key = crop_key(commodity)
    if key is None:
        return {"crop": None, "district": district, "points": [], "latest": None,
                "change_7d_pct": None, "sharp": False, "msp": None}
    t = await trend(session, crop=key, district=district, days=days)
    msp = official_msp(commodity)
    return {"crop": key, "district": district, "points": t.points, "latest": t.latest,
            "change_7d_pct": t.change_7d_pct, "sharp": t.sharp, "stale": t.stale,
            "days_since_latest": t.days_since_latest,
            "msp": msp["msp_inr_quintal"] if msp else None,
            "source": "AGMARKNET (DMI, MoA&FW) via data.gov.in"}


@router.get(
    "/advisories",
    response_model=list[AgriculturalAdvisory],
    dependencies=[Depends(RequirePermission(Permission.ADVISORY_READ))],
)
async def get_advisories(
    crop: str = Query(..., description="Crop name"),
    state: str | None = Query(None, description="State name"),
    district: str | None = Query(None, description="District name"),
    force_refresh: bool = Query(False, description="Bypass cache"),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> list[AgriculturalAdvisory]:
    """Retrieve active ICAR and State Agricultural Department agromet advisories."""
    service = LiveDataService(session=session)
    return await service.get_advisories(
        crop=crop,
        state=state,
        district=district,
        user_uuid=auth.user_uuid,
        force_refresh=force_refresh,
    )


@router.get(
    "/schemes",
    response_model=list[GovernmentScheme],
    dependencies=[Depends(RequirePermission(Permission.SCHEME_READ))],
)
async def get_government_schemes(
    state: str | None = Query(None, description="State name"),
    crop: str | None = Query(None, description="Target crop"),
    farmer_category: str | None = Query(None, description="Farmer category (Small/Marginal/Tenant)"),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> list[GovernmentScheme]:
    """Query official Central and State government welfare and subsidy schemes."""
    service = LiveDataService(session=session)
    return await service.get_government_schemes(
        state=state,
        crop=crop,
        farmer_category=farmer_category,
        user_uuid=auth.user_uuid,
    )


@router.get(
    "/schemes/{scheme_id}/eligibility",
    response_model=SchemeEligibilityEvaluation,
    dependencies=[Depends(RequirePermission(Permission.SCHEME_READ))],
)
async def evaluate_scheme_eligibility(
    scheme_id: str,
    landholding_acres: float | None = Query(None, description="Landholding in acres"),
    crop: str | None = Query(None, description="Crop name"),
    state: str | None = Query(None, description="State name"),
    farmer_category: str | None = Query(None, description="Farmer category"),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> SchemeEligibilityEvaluation:
    """Evaluate farmer eligibility for a specific government scheme."""
    service = LiveDataService(session=session)
    return await service.evaluate_scheme_eligibility(
        scheme_id=scheme_id,
        landholding_acres=landholding_acres,
        crop=crop,
        state=state,
        farmer_category=farmer_category,
    )
