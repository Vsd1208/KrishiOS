"""Prompt template registry for agent system and task prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Reusable prompt template with variable substitution."""

    template_id: str
    name: str
    system_instruction: str
    user_template: str
    variables: tuple[str, ...] = ()
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def render(self, **kwargs: Any) -> tuple[str, str | None]:
        """Render system instruction and user prompt with supplied variables."""
        user_prompt = self.user_template.format(**kwargs)
        return user_prompt, self.system_instruction or None


class PromptRegistry:
    """Registry of reusable prompt templates for agents."""

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._register_defaults()

    def register(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> PromptTemplate | None:
        """Return a template by identifier."""
        return self._templates.get(template_id)

    def list_templates(self) -> list[PromptTemplate]:
        """Return all registered templates."""
        return list(self._templates.values())

    def _register_defaults(self) -> None:
        """Register built-in agricultural prompt templates."""
        self.register(
            PromptTemplate(
                template_id="crop_advisory",
                name="Crop Advisory",
                system_instruction=(
                    "You are an expert ICAR agronomist giving precise, actionable guidance to Indian farmers. "
                    "Base recommendations only on the verified knowledge provided."
                ),
                user_template=(
                    "User Query: {query}\n"
                    "Crop: {crop}, Region: {region}, Season: {season}\n"
                    "Verified ICAR/Dept Knowledge:\n{context}\n\n"
                    "Generate actionable, grounded agricultural advice."
                ),
                variables=("query", "crop", "region", "season", "context"),
            )
        )
        self.register(
            PromptTemplate(
                template_id="govt_scheme",
                name="Government Scheme",
                system_instruction=(
                    "You are an official Ministry of Agriculture advisor detailing government welfare schemes. "
                    "Explain benefits, eligibility, and enrollment steps clearly."
                ),
                user_template=(
                    "Farmer Query: {query}\nState: {state}\n"
                    "Official Scheme Circulars:\n{context}\n\n"
                    "Explain the scheme benefits, eligibility criteria, and enrollment process."
                ),
                variables=("query", "state", "context"),
            )
        )
        self.register(
            PromptTemplate(
                template_id="officer_briefing",
                name="Officer Briefing",
                system_instruction=(
                    "You are a Chief Agricultural Administrative Officer summarizing district field operations."
                ),
                user_template=(
                    "Officer Task: {task}\n"
                    "District: {district}, State: {state}\n\n"
                    "Prepare an executive administrative briefing with key takeaways and field action items."
                ),
                variables=("task", "district", "state"),
            )
        )
