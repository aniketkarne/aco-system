"""
Prompt Loader - Load agent system prompts from markdown files with YAML frontmatter.

This module handles loading agent definitions from markdown files in the agent_prompts/ directory.
Each file has YAML frontmatter with metadata (name, tools, model) followed by the system prompt.
"""
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional
from config.settings import get_settings


class PromptLoadError(Exception):
    """Error loading agent prompt file."""
    pass


def load_agent_prompt(agent_name: str) -> Tuple[str, Dict]:
    """
    Load agent system prompt from markdown file with YAML frontmatter.

    Args:
        agent_name: Name of the agent (e.g., "aco-pm", "planner")

    Returns:
        Tuple of (prompt_body, metadata_dict)

    Raises:
        PromptLoadError: If file not found or parsing fails
    """
    settings = get_settings()
    prompts_dir = Path(settings.AGENT_PROMPTS_DIR)

    # Try with and without prefix, and strip prefix if needed
    possible_files = [
        prompts_dir / f"{agent_name}.md",
        prompts_dir / f"aco-{agent_name}.md",  # For shorthand like "pm" → "aco-pm"
    ]
    # Also try stripping aco- prefix (e.g., "aco-pm" → "pm")
    if agent_name.startswith("aco-"):
        shorthand = agent_name[4:]  # strip "aco-" prefix
        possible_files.append(prompts_dir / f"{shorthand}.md")
        possible_files.insert(0, prompts_dir / f"{shorthand}.md")  # Try shorthand first

    prompt_file = None
    for file_path in possible_files:
        if file_path.exists():
            prompt_file = file_path
            break

    if not prompt_file:
        raise PromptLoadError(
            f"Agent prompt file not found for '{agent_name}'. "
            f"Looked in: {[str(f) for f in possible_files]}"
        )

    # Read file content
    content = prompt_file.read_text()

    # Split into max 3 parts: [before frontmatter, frontmatter, body]
    # The file starts with ---, so parts[0] will be empty string
    parts = content.split('---', 2)

    if len(parts) < 3:
        raise PromptLoadError(
            f"Invalid frontmatter format in {prompt_file}. "
            f"Expected format: ---\\nYAML\\n---\\nPrompt Body"
        )

    # Parse YAML frontmatter
    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        raise PromptLoadError(f"Failed to parse YAML frontmatter in {prompt_file}: {e}")

    # Extract prompt body (after second ---)
    prompt_body = parts[2].strip()

    return prompt_body, metadata


def get_all_agents() -> Dict[str, Dict]:
    """
    Load all agent prompts from the agent_prompts directory.

    Returns:
        Dictionary mapping agent names to their (prompt_body, metadata) tuples
    """
    settings = get_settings()
    prompts_dir = Path(settings.AGENT_PROMPTS_DIR)

    if not prompts_dir.exists():
        return {}

    agents = {}
    for prompt_file in prompts_dir.glob("*.md"):
        agent_name = prompt_file.stem  # Remove .md extension
        try:
            prompt_body, metadata = load_agent_prompt(agent_name)
            agents[agent_name] = {
                "prompt": prompt_body,
                "metadata": metadata
            }
        except PromptLoadError as e:
            # Log error but continue loading other agents
            import logging
            logging.warning(f"Failed to load agent {agent_name}: {e}")

    return agents


def resolve_agent_name(name: str) -> str:
    """
    Resolve shorthand agent names to full names.

    Examples:
        "pm" → "aco-pm"
        "planner" → "aco-planner"
        "aco-pm" → "aco-pm"
    """
    # If already has prefix, return as-is
    if name.startswith("aco-"):
        return name

    # Otherwise, add prefix
    return f"aco-{name}"


def get_agent_tools(agent_name: str) -> list:
    """
    Get list of allowed tools for an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        List of tool names the agent is allowed to use

    Raises:
        PromptLoadError: If agent file not found
    """
    prompt_body, metadata = load_agent_prompt(agent_name)
    return metadata.get("tools", [])


def get_agent_model(agent_name: str) -> Optional[str]:
    """
    Get the model name configured for an agent.

    Resolution order:
    1. Explicit per-agent override (ACO_<AGENT>_MODEL env var), if set.
    2. The shared tier default from AGENT_MODELS (MODEL_OPU / MODEL_SONNET /
       MODEL_HAIKU).

    Args:
        agent_name: Name of the agent

    Returns:
        Model name string (e.g., "claude-sonnet-5-5") or "none"

    Raises:
        PromptLoadError: If agent file not found
    """
    resolved_name = resolve_agent_name(agent_name)

    override = get_agent_model_override(resolved_name)
    if override is not None:
        return override

    # Check settings for model assignment
    settings = get_settings()
    model_key = settings.AGENT_MODELS.get(resolved_name, "MODEL_SONNET")

    # If model_key is "none", return "none"
    if model_key == "none":
        return "none"

    # Get actual model name from settings
    model_name = getattr(settings, model_key, model_key)
    return model_name


def get_agent_model_override(resolved_name: str) -> Optional[str]:
    """
    Get the explicit per-agent model override from the environment.

    The .env.example documents these as ACO-PM_MODEL, ACO-ARCHITECT_MODEL and
    so on. Both the hyphenated and underscored spellings are accepted, and
    the value is used verbatim, so it must be a model ID the configured
    provider accepts.

    Args:
        resolved_name: Fully-qualified agent name (e.g. "aco-architect")

    Returns:
        The override value, "none" to disable the LLM for the agent, or None
        when no override is configured.
    """
    suffix = resolved_name.removeprefix("aco-").upper().replace("-", "_")
    field = f"ACO_{suffix}_MODEL"

    settings = get_settings()
    value = getattr(settings, field, None)
    if value is None:
        return None

    value = str(value).strip()
    return value or None


def validate_agent_prompt(agent_name: str) -> Dict:
    """
    Validate an agent prompt file for required fields.

    Args:
        agent_name: Name of the agent

    Returns:
        Dictionary with validation results:
        - valid: bool
        - errors: list of error messages
        - warnings: list of warning messages
    """
    errors = []
    warnings = []

    try:
        prompt_body, metadata = load_agent_prompt(agent_name)
    except PromptLoadError as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": []
        }

    # Check required metadata fields
    required_fields = ["name", "description"]
    for field in required_fields:
        if field not in metadata:
            errors.append(f"Missing required metadata field: {field}")

    # Check recommended metadata fields
    recommended_fields = ["tools", "model"]
    for field in recommended_fields:
        if field not in metadata:
            warnings.append(f"Missing recommended metadata field: {field}")

    # Check prompt body is not empty
    if not prompt_body:
        errors.append("Prompt body is empty")

    # Check tools is a list if present
    if "tools" in metadata and not isinstance(metadata["tools"], list):
        errors.append("Metadata field 'tools' must be a list")

    # Check prompt body has sufficient content
    if len(prompt_body) < 100:
        warnings.append(f"Prompt body is very short ({len(prompt_body)} chars). Ensure it's comprehensive.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
