"""Concrete Agricultural Relevance Rules for KrishiOS."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.events.contracts import EventEnvelope, EventType
from app.models.proactive import RiskSeverity
from app.proactive.rules.base import BaseRelevanceRule, RuleResult


class HeavyRainfallRule(BaseRelevanceRule):
    """Evaluates heavy precipitation forecasts against field soil drainage and crop sensitivity."""

    @property
    def rule_id(self) -> str:
        return "RULE_AGRI_HEAVY_RAIN_001"

    @property
    def rule_name(self) -> str:
        return "Heavy Rainfall & Waterlogging Sensitivity Rule"

    @property
    def supported_events(self) -> list[str]:
        return [EventType.WEATHER_ALERT, EventType.HEAVY_RAIN_EXPECTED]

    async def evaluate(self, event: EventEnvelope, context: dict[str, Any]) -> RuleResult:
        payload = event.payload or {}
        rainfall_mm = float(payload.get("rainfall_mm", payload.get("precipitation_mm", 0.0)))
        probability = float(payload.get("probability", 1.0))

        # Check rainfall threshold
        if rainfall_mm < 40.0:
            return RuleResult(
                matched=False,
                rule_id=self.rule_id,
                risk_type="weather.heavy_rainfall",
                reason=f"Rainfall {rainfall_mm}mm is below actionable threshold (40mm)",
            )

        crop_name = str(context.get("crop", "")).strip().lower()
        soil_type = str(context.get("soil_type", "")).strip().lower()
        has_active_field = bool(context.get("field_id"))

        # Determine severity based on precipitation volume and crop/soil conditions
        if rainfall_mm >= 100.0:
            severity = RiskSeverity.CRITICAL
        elif rainfall_mm >= 65.0:
            severity = RiskSeverity.HIGH
        else:
            severity = RiskSeverity.MEDIUM

        # Soil drainage factor (e.g. black clay soil holds water longer -> elevated risk)
        poor_drainage = any(s in soil_type for s in ["clay", "black", "heavy", "poor"])
        if poor_drainage and severity == RiskSeverity.MEDIUM:
            severity = RiskSeverity.HIGH

        confidence = min(0.95, 0.70 + (probability * 0.25))

        reason = (
            f"Forecast predicts {rainfall_mm:.1f}mm rainfall with {probability * 100:.0f}% confidence. "
            f"Field with {soil_type or 'standard'} soil and active {crop_name or 'standing'} crop "
            f"has elevated waterlogging and root aeration risk."
        )

        return RuleResult(
            matched=True,
            rule_id=self.rule_id,
            risk_type="weather.heavy_rainfall",
            severity=severity,
            confidence=confidence,
            reason=reason,
            evidence={
                "rainfall_mm": rainfall_mm,
                "probability": probability,
                "soil_type": soil_type,
                "crop": crop_name,
                "poor_drainage": poor_drainage,
            },
            recommended_action_summary="Ensure field drainage channels are clear to prevent water stagnation.",
        )


class ExtremeHeatRule(BaseRelevanceRule):
    """Evaluates heatwave conditions causing moisture stress."""

    @property
    def rule_id(self) -> str:
        return "RULE_AGRI_HEAT_002"

    @property
    def rule_name(self) -> str:
        return "Extreme Heatwave & Moisture Stress Rule"

    @property
    def supported_events(self) -> list[str]:
        return [EventType.WEATHER_ALERT, EventType.EXTREME_HEAT]

    async def evaluate(self, event: EventEnvelope, context: dict[str, Any]) -> RuleResult:
        payload = event.payload or {}
        max_temp = float(payload.get("max_temperature_celsius", payload.get("temperature_celsius", 0.0)))

        if max_temp < 39.0:
            return RuleResult(
                matched=False,
                rule_id=self.rule_id,
                risk_type="weather.extreme_heat",
                reason=f"Temperature {max_temp}°C is below extreme heat threshold (39°C)",
            )

        severity = RiskSeverity.HIGH if max_temp >= 43.0 else RiskSeverity.MEDIUM
        crop_name = str(context.get("crop", "")).strip()

        return RuleResult(
            matched=True,
            rule_id=self.rule_id,
            risk_type="weather.extreme_heat",
            severity=severity,
            confidence=0.88,
            reason=f"Forecast indicates extreme maximum temperature of {max_temp:.1f}°C, increasing evapotranspiration.",
            evidence={"max_temperature_celsius": max_temp, "crop": crop_name},
            recommended_action_summary="Apply light evening irrigation or mulching to mitigate heat stress.",
        )


class DiseaseRiskRule(BaseRelevanceRule):
    """Evaluates weather microclimate (humidity + temperature) and host crop susceptibility for fungal/bacterial diseases."""

    @property
    def rule_id(self) -> str:
        return "RULE_AGRI_DISEASE_003"

    @property
    def rule_name(self) -> str:
        return "Fungal and Bacterial Microclimate Risk Rule"

    @property
    def supported_events(self) -> list[str]:
        return [
            EventType.DISEASE_RISK_CHANGED,
            EventType.HIGH_HUMIDITY,
            EventType.WEATHER_ALERT,
            EventType.VISION_RISK_DETECTED,
        ]

    async def evaluate(self, event: EventEnvelope, context: dict[str, Any]) -> RuleResult:
        payload = event.payload or {}
        crop = str(context.get("crop", payload.get("crop", ""))).strip().lower()
        humidity = float(payload.get("relative_humidity_percent", payload.get("humidity", 0.0)))
        temp = float(payload.get("temperature_celsius", payload.get("temp", 25.0)))
        vision_findings = context.get("recent_vision_findings", [])

        # Microclimate condition for fungal pathogens: Humidity > 75% and Temp between 20°C and 32°C
        favorable_weather = humidity >= 75.0 and (20.0 <= temp <= 32.0)
        has_vision_precursor = len(vision_findings) > 0
        direct_disease_event = event.event_type == EventType.DISEASE_RISK_CHANGED

        if not (favorable_weather or has_vision_precursor or direct_disease_event):
            return RuleResult(
                matched=False,
                rule_id=self.rule_id,
                risk_type="agronomy.disease_risk",
                reason="Environmental conditions (humidity/temp) do not meet pathogenic incubation thresholds.",
            )

        # Susceptible crops check
        susceptible_crops = {"paddy", "rice", "cotton", "tomato", "chilli", "potato", "groundnut", "maize"}
        is_susceptible = any(c in crop for c in susceptible_crops) if crop else False

        severity = RiskSeverity.MEDIUM
        confidence = 0.75

        if has_vision_precursor and favorable_weather:
            severity = RiskSeverity.HIGH
            confidence = 0.90
        elif direct_disease_event and is_susceptible:
            severity = RiskSeverity.HIGH
            confidence = float(payload.get("confidence", 0.85))

        reason = (
            f"Microclimate ({humidity:.0f}% humidity, {temp:.1f}°C) creates favorable incubation for fungal spores. "
            f"Target crop '{crop or 'general'}' is susceptible."
        )

        return RuleResult(
            matched=True,
            rule_id=self.rule_id,
            risk_type="agronomy.disease_risk",
            severity=severity,
            confidence=confidence,
            reason=reason,
            evidence={
                "humidity_percent": humidity,
                "temperature_celsius": temp,
                "crop": crop,
                "has_vision_precursor": has_vision_precursor,
                "vision_findings_count": len(vision_findings),
            },
            recommended_action_summary="Monitor fields closely for initial leaf spotting or blast symptoms.",
        )


class MarketPriceVolatilityRule(BaseRelevanceRule):
    """Evaluates significant mandi commodity price shifts against farmer cultivation."""

    @property
    def rule_id(self) -> str:
        return "RULE_AGRI_MARKET_004"

    @property
    def rule_name(self) -> str:
        return "Mandi Price Volatility & Trend Rule"

    @property
    def supported_events(self) -> list[str]:
        return [EventType.MARKET_PRICE_CHANGED, EventType.PRICE_ANOMALY_DETECTED]

    async def evaluate(self, event: EventEnvelope, context: dict[str, Any]) -> RuleResult:
        payload = event.payload or {}
        commodity = str(payload.get("commodity", "")).strip().lower()
        change_pct = float(payload.get("change_percent", payload.get("price_change_pct", 0.0)))
        current_price = float(payload.get("current_price", payload.get("modal_price", 0.0)))
        farmer_crop = str(context.get("crop", "")).strip().lower()

        # Check if farmer grows this commodity
        if farmer_crop and commodity and (commodity not in farmer_crop and farmer_crop not in commodity):
            return RuleResult(
                matched=False,
                rule_id=self.rule_id,
                risk_type="market.price_volatility",
                reason=f"Commodity '{commodity}' does not match farmer crop '{farmer_crop}'",
            )

        # Meaningful threshold: abs(change) >= 10%
        if abs(change_pct) < 10.0:
            return RuleResult(
                matched=False,
                rule_id=self.rule_id,
                risk_type="market.price_volatility",
                reason=f"Price change {change_pct:+.1f}% is below 10% notification threshold",
            )

        severity = RiskSeverity.HIGH if abs(change_pct) >= 20.0 else RiskSeverity.MEDIUM
        direction = "dropped" if change_pct < 0 else "surged"

        return RuleResult(
            matched=True,
            rule_id=self.rule_id,
            risk_type="market.price_volatility",
            severity=severity,
            confidence=0.92,
            reason=f"Mandi price for {commodity.title()} {direction} by {abs(change_pct):.1f}% to ₹{current_price:.0f}/quintal.",
            evidence={
                "commodity": commodity,
                "current_price": current_price,
                "change_percent": change_pct,
                "market": payload.get("market", "Local Mandi"),
            },
            recommended_action_summary=f"Consider market timing; prices have {direction} significantly.",
        )


class SchemeEligibilityRule(BaseRelevanceRule):
    """Evaluates newly published or updated government scheme eligibility against farmer profile."""

    @property
    def rule_id(self) -> str:
        return "RULE_AGRI_SCHEME_005"

    @property
    def rule_name(self) -> str:
        return "Government Scheme Eligibility & Deadline Rule"

    @property
    def supported_events(self) -> list[str]:
        return [EventType.GOVERNMENT_SCHEME_UPDATED]

    async def evaluate(self, event: EventEnvelope, context: dict[str, Any]) -> RuleResult:
        payload = event.payload or {}
        scheme_name = str(payload.get("scheme_name", payload.get("title", "")))
        scheme_state = str(payload.get("state", "")).strip().lower()
        max_landholding = payload.get("max_landholding_acres")

        farmer_state = str(context.get("state", "")).strip().lower()
        farmer_landholding = float(context.get("landholding_acres", 0.0))

        # Check state geographic match
        if scheme_state and scheme_state != "all" and farmer_state and scheme_state not in farmer_state:
            return RuleResult(
                matched=False,
                rule_id=self.rule_id,
                risk_type="scheme.eligibility",
                reason=f"Scheme applies to '{scheme_state}', but farmer is registered in '{farmer_state}'",
            )

        # Check landholding eligibility if specified
        if max_landholding is not None and farmer_landholding > float(max_landholding):
            return RuleResult(
                matched=False,
                rule_id=self.rule_id,
                risk_type="scheme.eligibility",
                reason=f"Farmer landholding ({farmer_landholding} acres) exceeds scheme limit ({max_landholding} acres)",
            )

        return RuleResult(
            matched=True,
            rule_id=self.rule_id,
            risk_type="scheme.eligibility",
            severity=RiskSeverity.LOW,
            confidence=0.95,
            reason=f"Farmer profile in {farmer_state or 'India'} matches eligibility criteria for '{scheme_name}'.",
            evidence={
                "scheme_name": scheme_name,
                "scheme_code": payload.get("scheme_code"),
                "farmer_landholding_acres": farmer_landholding,
                "deadline": payload.get("application_deadline"),
            },
            recommended_action_summary=f"Eligible for {scheme_name}. Check application requirements before deadline.",
        )


class RuleRegistry:
    """Registry maintaining active relevance rules for the proactive engine."""

    def __init__(self) -> None:
        self._rules: dict[str, BaseRelevanceRule] = {}
        # Register default rules
        self.register(HeavyRainfallRule())
        self.register(ExtremeHeatRule())
        self.register(DiseaseRiskRule())
        self.register(MarketPriceVolatilityRule())
        self.register(SchemeEligibilityRule())

    def register(self, rule: BaseRelevanceRule) -> None:
        """Register a new agricultural relevance rule."""
        self._rules[rule.rule_id] = rule
        logger.debug("RuleRegistry: registered rule '{}'", rule.rule_id)

    def get_rules_for_event(self, event_type: str) -> list[BaseRelevanceRule]:
        """Return all rules that support the given event type."""
        return [
            rule
            for rule in self._rules.values()
            if event_type in rule.supported_events or "*" in rule.supported_events
        ]

    async def evaluate_all(
        self, event: EventEnvelope, context: dict[str, Any]
    ) -> list[RuleResult]:
        """Evaluate all matching rules for an event and context."""
        matching_rules = self.get_rules_for_event(event.event_type)
        results: list[RuleResult] = []
        for rule in matching_rules:
            try:
                res = await rule.evaluate(event, context)
                if res.matched:
                    results.append(res)
            except Exception as exc:
                logger.exception("RuleRegistry: error evaluating rule '{}': {}", rule.rule_id, exc)
        return results
