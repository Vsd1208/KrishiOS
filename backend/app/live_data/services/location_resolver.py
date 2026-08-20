"""Location resolution service traversing Farmer -> Field -> Coordinates/District."""

from dataclasses import dataclass
from uuid import UUID
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.district import District
from app.models.farmer import Farmer
from app.models.field import Field
from app.models.officer import Officer
from app.models.user import User, UserRole


@dataclass(frozen=True, slots=True)
class ResolvedLocation:
    """Standardized location context for live agricultural queries."""

    latitude: float
    longitude: float
    state: str
    district: str
    village: str | None = None
    field_id: int | None = None
    farmer_id: int | None = None
    is_approximate: bool = False

    @property
    def privacy_coords(self) -> tuple[float, float]:
        """Return coordinates truncated to 2 decimal places (~1.1 km) for external vendor privacy."""
        return round(self.latitude, 2), round(self.longitude, 2)


class LocationResolver:
    """Resolves coordinates and administrative location from various context inputs."""

    DEFAULT_STATE = "Telangana"
    DEFAULT_DISTRICT = "Warangal"
    DEFAULT_LAT = 17.9689
    DEFAULT_LON = 79.5941

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def resolve(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        district: str | None = None,
        state: str | None = None,
        field_id: int | None = None,
        user_uuid: UUID | None = None,
    ) -> ResolvedLocation:
        """Resolve location in priority order: coordinates -> field_id -> user_uuid -> district name -> defaults."""

        # 1. Explicit coordinates provided
        if latitude is not None and longitude is not None:
            return ResolvedLocation(
                latitude=float(latitude),
                longitude=float(longitude),
                state=state or self.DEFAULT_STATE,
                district=district or self.DEFAULT_DISTRICT,
                field_id=field_id,
                is_approximate=False,
            )

        # 2. Field ID provided
        if field_id is not None and self._session is not None:
            stmt = (
                select(Field)
                .options(
                    selectinload(Field.farmer).selectinload(Farmer.district)
                )
                .where(Field.id == field_id, Field.deleted_at.is_(None))
            )
            res = await self._session.execute(stmt)
            field = res.scalar_one_or_none() if hasattr(res, "scalar_one_or_none") else None
            if isinstance(field, Field):
                dist_name = field.farmer.district.district_name if field.farmer and field.farmer.district else self.DEFAULT_DISTRICT
                st_name = field.farmer.district.state if field.farmer and field.farmer.district else self.DEFAULT_STATE
                return ResolvedLocation(
                    latitude=float(field.latitude),
                    longitude=float(field.longitude),
                    state=st_name,
                    district=dist_name,
                    village=field.farmer.village if field.farmer else None,
                    field_id=field.id,
                    farmer_id=field.farmer_id,
                    is_approximate=False,
                )

        # 3. User UUID provided (Traverse User -> Farmer -> Field)
        if user_uuid is not None and self._session is not None:
            stmt = select(User).where(User.uuid == user_uuid, User.is_active.is_(True))
            res = await self._session.execute(stmt)
            user = res.scalar_one_or_none() if hasattr(res, "scalar_one_or_none") else None

            if isinstance(user, User):
                if user.role == UserRole.FARMER and user.farmer_profile_id is not None:
                    f_stmt = (
                        select(Farmer)
                        .options(
                            selectinload(Farmer.fields),
                            selectinload(Farmer.district),
                        )
                        .where(Farmer.id == user.farmer_profile_id, Farmer.deleted_at.is_(None))
                    )
                    f_res = await self._session.execute(f_stmt)
                    farmer = f_res.scalar_one_or_none() if hasattr(f_res, "scalar_one_or_none") else None
                    if isinstance(farmer, Farmer):
                        dist_name = farmer.district.district_name if farmer.district else self.DEFAULT_DISTRICT
                        st_name = farmer.district.state if farmer.district else self.DEFAULT_STATE
                        # Pick first active field if available
                        active_field = next((f for f in farmer.fields if not f.is_deleted), None)
                        if active_field is not None:
                            return ResolvedLocation(
                                latitude=float(active_field.latitude),
                                longitude=float(active_field.longitude),
                                state=st_name,
                                district=dist_name,
                                village=farmer.village,
                                field_id=active_field.id,
                                farmer_id=farmer.id,
                                is_approximate=False,
                            )
                        # Otherwise use district centroid
                        lat = float(farmer.district.latitude) if farmer.district else self.DEFAULT_LAT
                        lon = float(farmer.district.longitude) if farmer.district else self.DEFAULT_LON
                        return ResolvedLocation(
                            latitude=lat,
                            longitude=lon,
                            state=st_name,
                            district=dist_name,
                            village=farmer.village,
                            farmer_id=farmer.id,
                            is_approximate=True,
                        )

                elif user.role == UserRole.OFFICER and user.officer_profile_id is not None:
                    o_stmt = (
                        select(Officer)
                        .options(selectinload(Officer.district))
                        .where(Officer.id == user.officer_profile_id, Officer.deleted_at.is_(None))
                    )
                    o_res = await self._session.execute(o_stmt)
                    officer = o_res.scalar_one_or_none() if hasattr(o_res, "scalar_one_or_none") else None
                    if isinstance(officer, Officer) and officer.district is not None:
                        return ResolvedLocation(
                            latitude=float(officer.district.latitude),
                            longitude=float(officer.district.longitude),
                            state=officer.district.state,
                            district=officer.district.district_name,
                            is_approximate=True,
                        )

        # 4. District name lookup
        if district is not None and self._session is not None:
            d_stmt = select(District).where(District.district_name.ilike(district), District.deleted_at.is_(None))
            d_res = await self._session.execute(d_stmt)
            d_obj = d_res.scalar_one_or_none() if hasattr(d_res, "scalar_one_or_none") else None
            if isinstance(d_obj, District):
                return ResolvedLocation(
                    latitude=float(d_obj.latitude),
                    longitude=float(d_obj.longitude),
                    state=d_obj.state,
                    district=d_obj.district_name,
                    is_approximate=True,
                )

        # 5. Fallback Default
        return ResolvedLocation(
            latitude=self.DEFAULT_LAT,
            longitude=self.DEFAULT_LON,
            state=state or self.DEFAULT_STATE,
            district=district or self.DEFAULT_DISTRICT,
            is_approximate=True,
        )
