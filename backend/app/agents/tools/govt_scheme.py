"""Production Agent Tool for Government Welfare & Subsidy Schemes."""

from time import perf_counter
from typing import Any

from app.agents.contracts.tool import BaseTool, RetryPolicy, ToolMetadata, ToolResult
from app.auth.permissions import Permission
from app.live_data.services.live_data_service import LiveDataService


class GovernmentSchemeTool(BaseTool):
    """Queries official government welfare schemes (PM-KISAN, PMFBY, Rythu Bharosa) and evaluates eligibility."""

    def __init__(self, service: LiveDataService | None = None) -> None:
        metadata = ToolMetadata(
            name="government_scheme",
            description=(
                "Query verified Central and State Government agricultural welfare schemes, "
                "subsidies, and crop insurance programs, and evaluate farmer eligibility."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "State name (e.g. Telangana)"},
                    "crop": {"type": "string", "description": "Crop name (e.g. Paddy, Cotton)"},
                    "farmer_category": {"type": "string", "description": "Farmer category (e.g. Small, Marginal, Tenant)"},
                    "landholding_acres": {"type": "number", "description": "Farmer landholding size in acres"},
                    "scheme_id": {"type": "string", "description": "Optional scheme ID to evaluate specific eligibility"},
                },
            },
            permissions=[Permission.SCHEME_READ, Permission.LIVE_DATA_READ],
            timeout_seconds=5.0,
            retry_policy=RetryPolicy(max_retries=2, backoff_seconds=0.5),
            supported_agent_types=["crop_advisory_agent", "govt_agent", "officer_agent"],
        )
        super().__init__(metadata)
        self._service = service or LiveDataService()

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        st = parameters.get("state")
        crop = parameters.get("crop")
        f_cat = parameters.get("farmer_category")
        acres = float(parameters["landholding_acres"]) if parameters.get("landholding_acres") is not None else None
        sid = parameters.get("scheme_id")

        try:
            if sid:
                # Evaluate specific scheme eligibility
                eval_res = await self._service.evaluate_scheme_eligibility(
                    scheme_id=sid,
                    landholding_acres=acres,
                    crop=crop,
                    state=st,
                    farmer_category=f_cat,
                )
                data = {
                    "evaluation": {
                        "scheme_id": eval_res.scheme.scheme_id,
                        "scheme_name": eval_res.scheme.name,
                        "eligibility": eval_res.eligibility.value,
                        "reason": eval_res.reason,
                        "benefits": eval_res.scheme.benefits,
                        "portal": eval_res.scheme.official_portal_url,
                        "missing_criteria": eval_res.missing_criteria,
                    }
                }
            else:
                # Query matching schemes
                schemes = await self._service.get_government_schemes(
                    state=st,
                    crop=crop,
                    farmer_category=f_cat,
                )
                data = {
                    "schemes_count": len(schemes),
                    "schemes": [
                        {
                            "scheme_id": s.scheme_id,
                            "name": s.name,
                            "description": s.description,
                            "benefits": s.benefits,
                            "subsidy": s.subsidy_amount_or_percent,
                            "portal": s.official_portal_url,
                            "status": s.status,
                        }
                        for s in schemes
                    ],
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
