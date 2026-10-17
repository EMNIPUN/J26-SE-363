"""Pydantic prompt library loader and renderer for com_agent.

Strictly aligned with:
- BOARD.md T4.1 (T4.1.1 - T4.1.4)
- PLAN.md Section 6.1 (Pydantic Prompt Schema)
"""

import pathlib
from typing import Dict, List, Any, Optional, Tuple
import yaml
from pydantic import BaseModel, Field, ConfigDict, ValidationError


class PromptDefinition(BaseModel):
    """Pydantic model representing a single guardrailed prompt definition."""
    model_config = ConfigDict(extra="ignore")

    prompt_id: str = Field(..., description="Unique prompt identifier")
    version: str = Field(default="1.0.0", description="Prompt version")
    role: str = Field(..., description="System persona and expertise definition")
    objective: str = Field(..., description="Clear definition of synthesis task")
    strict_constraints: List[str] = Field(..., description="Inviolable guardrails")
    input_variables: List[str] = Field(..., description="Expected dynamic placeholders")
    output_schema_format: str = Field(..., description="Expected structure (markdown, json)")
    model_parameters: Dict[str, Any] = Field(
        default_factory=lambda: {"temperature": 0.2, "top_p": 0.95}
    )
    system_prompt_template: str = Field(..., description="System prompt template")
    user_prompt_template: str = Field(..., description="User prompt template")


class PromptLibrary(BaseModel):
    """Pydantic model holding all versioned prompt definitions."""
    model_config = ConfigDict(extra="ignore")

    version: str = Field(default="1.0.0", description="Library version")
    prompts: Dict[str, PromptDefinition] = Field(default_factory=dict)


def load_prompt_library(yaml_path: Optional[pathlib.Path] = None) -> PromptLibrary:
    """Read and validate prompts YAML against PromptLibrary schema.

    Raises:
        FileNotFoundError: If the YAML file is missing.
        ValidationError: If schema or structure fails Pydantic validation.
    """
    if yaml_path is None:
        yaml_path = pathlib.Path(__file__).resolve().parent / "prompts.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Prompts YAML configuration not found at {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return PromptLibrary(**data)


def render_prompt(
    prompt_def: PromptDefinition, variables: Dict[str, Any]
) -> Tuple[str, str]:
    """Render system and user prompt strings with dynamic variables.

    Raises:
        KeyError: If any declared input_variable is missing from variables.

    Returns:
        (system_prompt, user_prompt)
    """
    # 1. Validate all declared input_variables are present
    missing = [var for var in prompt_def.input_variables if var not in variables]
    if missing:
        raise KeyError(
            f"Missing required input variable(s) for prompt '{prompt_def.prompt_id}': {missing}"
        )

    # 2. Merge definition defaults and dynamic variables
    formatted_constraints = "\n".join(f"- {c}" for c in prompt_def.strict_constraints)
    all_vars: Dict[str, Any] = {
        "role": prompt_def.role,
        "objective": prompt_def.objective,
        "strict_constraints": formatted_constraints,
        **variables,
    }

    # 3. Format templates
    system_prompt = prompt_def.system_prompt_template.format(**all_vars).strip()
    user_prompt = prompt_def.user_prompt_template.format(**all_vars).strip()

    return system_prompt, user_prompt
