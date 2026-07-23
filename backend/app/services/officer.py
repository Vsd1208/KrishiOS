"""Officer business service for district staff management."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.domain import EntityConflictError
from app.models.officer import Officer
from app.repositories.district import DistrictRepository
from app.repositories.officer import OfficerRepository
from app.schemas.officer import OfficerCreate, OfficerUpdate
from app.services.base import BaseService


class OfficerService(BaseService):
    """Application service for officer lifecycle operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.officers = OfficerRepository(session)
        self.districts = DistrictRepository(session)

    async def register_officer(self, payload: OfficerCreate) -> Officer:
        await self._get_required(self.districts, payload.district_id, "District")
        await self._ensure_unique_contact(payload.email, payload.phone)
        officer = await self.officers.create(payload.model_dump())
        await self._commit()
        return officer

    async def update_officer(self, officer_id: int, payload: OfficerUpdate) -> Officer:
        officer = await self.get_officer(officer_id)
        values = payload.model_dump(exclude_unset=True)
        if "district_id" in values:
            await self._get_required(self.districts, values["district_id"], "District")
        if "email" in values:
            existing = await self.officers.get_by_email(values["email"])
            if existing is not None and existing.id != officer.id:
                raise EntityConflictError("Officer email is already registered")
        if "phone" in values:
            existing = await self.officers.get_by_phone(values["phone"])
            if existing is not None and existing.id != officer.id:
                raise EntityConflictError("Officer phone number is already registered")
        updated = await self.officers.update(officer, values)
        await self._commit()
        return updated

    async def list_officers(self, *, offset: int = 0, limit: int = 100) -> Sequence[Officer]:
        return await self.officers.list(offset=offset, limit=limit)

    async def get_officer(self, officer_id: int) -> Officer:
        return await self._get_required(  # type: ignore[return-value]
            self.officers,
            officer_id,
            "Officer",
        )

    async def delete_officer(self, officer_id: int) -> None:
        officer = await self.get_officer(officer_id)
        await self.officers.soft_delete(officer)
        await self._commit()

    async def _ensure_unique_contact(self, email: str, phone: str) -> None:
        if await self.officers.get_by_email(email) is not None:
            raise EntityConflictError("Officer email is already registered")
        if await self.officers.get_by_phone(phone) is not None:
            raise EntityConflictError("Officer phone number is already registered")
