"""Unit tests for repository data-access query behavior."""

from unittest.mock import AsyncMock

import pytest

from app.repositories.farmer import FarmerRepository


@pytest.mark.asyncio
async def test_farmer_repository_filters_by_phone(mock_session: AsyncMock) -> None:
    expected_farmer = object()
    scalar_result = AsyncMock()
    scalar_result.one_or_none.return_value = expected_farmer
    mock_session.scalars.return_value = scalar_result

    repository = FarmerRepository(mock_session)
    farmer = await repository.get_by_phone("9876543210")

    assert farmer is expected_farmer
    mock_session.scalars.assert_awaited_once()

