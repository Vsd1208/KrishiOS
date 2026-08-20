"""Production Agent Tool for Mandi & Commodity Prices."""

from time import perf_counter
from typing import Any

from app.agents.contracts.tool import BaseTool, RetryPolicy, ToolMetadata, ToolResult
from app.auth.permissions import Permission
from app.live_data.services.live_data_service import LiveDataService


class MandiPriceTool(BaseTool):
    """Fetches real-time mandi prices, modal price trends, and MSP benchmarks."""

    def __init__(self, service: LiveDataService | None = None) -> None:
        metadata = ToolMetadata(
            name="mandi_price",
            description=(
                "Fetch verified agricultural commodity market prices, modal prices (₹/quintal), "
                "Minimum Support Price (MSP), and price trends from Agmarknet/e-NAM mandis."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "commodity": {"type": "string", "description": "Commodity name (e.g. Paddy, Cotton, Wheat)"},
                    "state": {"type": "string", "description": "State name (e.g. Telangana, Punjab)"},
                    "district": {"type": "string", "description": "District name (e.g. Warangal, Ludhiana)"},
                },
                "required": ["commodity"],
            },
            permissions=[Permission.MARKET_READ, Permission.LIVE_DATA_READ],
            timeout_seconds=5.0,
            retry_policy=RetryPolicy(max_retries=2, backoff_seconds=0.5),
            supported_agent_types=["crop_advisory_agent", "crop_agent", "officer_agent"],
        )
        super().__init__(metadata)
        self._service = service or LiveDataService()

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        comm = parameters.get("commodity", "")
        st = parameters.get("state")
        dist = parameters.get("district")

        if not comm:
            return ToolResult(
                tool_name=self.metadata.name,
                success=False,
                data={},
                duration_ms=(perf_counter() - t0) * 1000,
                error_message="Commodity parameter is required.",
            )

        try:
            prices = await self._service.get_market_prices(
                commodity=comm,
                state=st,
                district=dist,
            )

            if not prices:
                return ToolResult(
                    tool_name=self.metadata.name,
                    success=True,
                    data={
                        "commodity": comm,
                        "prices": [],
                        "message": f"No active market arrivals found for {comm} in {dist or st or 'region'}.",
                    },
                    duration_ms=(perf_counter() - t0) * 1000,
                )

            primary = prices[0]
            data = {
                "commodity": primary.commodity,
                "variety": primary.variety,
                "market": primary.market,
                "district": primary.district,
                "state": primary.state,
                "arrival_date": primary.arrival_date.isoformat(),
                "modal_price_inr_quintal": primary.modal_price_inr_quintal,
                "min_price_inr_quintal": primary.min_price_inr_quintal,
                "max_price_inr_quintal": primary.max_price_inr_quintal,
                "msp_inr_quintal": primary.msp_inr_quintal,
                "trend": primary.price_trend.value,
                "source": primary.source,
                "freshness": primary.freshness.value,
                "observed_at": primary.observed_at.isoformat(),
            }

            return ToolResult(
                tool_name=self.metadata.name,
                success=True,
                data=data,
                duration_ms=(perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.metadata.name,
                success=False,
                data={},
                duration_ms=(perf_counter() - t0) * 1000,
                error_message=str(exc),
            )
