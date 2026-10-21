"""
Configuration management for ACO system.
Loads from environment variables and .env file.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field


class Settings(BaseSettings):
    # GitHub
    GITHUB_TOKEN: str = Field(..., description="GitHub Personal Access Token")
    GITHUB_OWNER: str = Field(..., description="GitHub username/org")
    GITHUB_REPO: str = Field(..., description="Main repo name")
    
    # LLM Provider
    LLM_PROVIDER: str = Field("anthropic", description="openai, anthropic, xai, openrouter, or minimax")
    OPENAI_API_KEY: str | None = Field(None, description="OpenAI API key")
    ANTHROPIC_API_KEY: str | None = Field(None, description="Anthropic API key")
    XAI_API_KEY: str | None = Field(None, description="X.AI API key")
    OPENROUTER_API_KEY: str | None = Field(None, description="OpenRouter API key")
    MINIMAX_API_KEY: str | None = Field(None, description="MiniMax API key")

    # Per-provider model IDs.
    # ANTHROPIC_MODEL / OPENAI_MODEL / XAI_MODEL are bare provider IDs
    # (e.g. "claude-sonnet-5-5") because they are sent straight to that
    # provider's API. OPENROUTER_MODEL and MINIMAX_MODEL are sent to
    # OpenRouter / MiniMax, which use their own ID spellings.
    ANTHROPIC_MODEL: str = Field("claude-sonnet-5-5", description="Anthropic model for the default agent tier")
    OPENAI_MODEL: str = Field("gpt-6.1-sol", description="OpenAI model for the default agent tier")
    XAI_MODEL: str = Field("grok-4.7", description="xAI model for the default agent tier")
    OPENROUTER_MODEL: str = Field("minimax/minimax-m3", description="OpenRouter model to use (e.g., minimax/minimax-m3)")
    MINIMAX_MODEL: str = Field("MiniMax-M3", description="MiniMax model to use")

    # Output token cap sent to providers that require or benefit from one.
    # Kept generous because current reasoning models spend part of this budget
    # on thinking tokens; a small cap truncates the visible answer to empty.
    MAX_TOKENS: int = Field(16384, description="Default output token cap per request")

    # LLM Model Mappings (Anthropic model IDs, current as of 2026-10).
    # These are the tier defaults used when LLM_PROVIDER=anthropic.
    MODEL_OPU: str = Field("claude-opus-5-5", description="Opus model for complex reasoning")
    MODEL_SONNET: str = Field("claude-sonnet-5-5", description="Sonnet model for implementation")
    MODEL_HAIKU: str = Field("claude-haiku-5-5", description="Haiku model for status updates")

    # Agent Model Assignments
    AGENT_MODELS: dict = Field(
        default={
            "aco-pm": "MODEL_SONNET",
            "aco-planner": "MODEL_OPU",
            "aco-architect": "MODEL_OPU",
            "aco-dev": "MODEL_SONNET",
            "aco-qa": "MODEL_SONNET",
            "aco-human": "none",  # No LLM needed for human reviewer
        },
        description="Which model each agent uses (maps to MODEL_* keys or 'none')"
    )

    # Per-agent model overrides. These win over AGENT_MODELS and are used
    # verbatim, so the value must be a model ID the configured provider
    # accepts. Both the underscore and hyphen spellings are accepted because
    # the hyphen form is what .env.example documents.
    ACO_PM_MODEL: str | None = Field(
        None,
        validation_alias=AliasChoices("ACO_PM_MODEL", "ACO-PM-MODEL"),
        description="Override model for aco-pm (e.g., claude-sonnet-5-5)",
    )
    ACO_PLANNER_MODEL: str | None = Field(
        None,
        validation_alias=AliasChoices("ACO_PLANNER_MODEL", "ACO-PLANNER-MODEL"),
        description="Override model for aco-planner",
    )
    ACO_ARCHITECT_MODEL: str | None = Field(
        None,
        validation_alias=AliasChoices("ACO_ARCHITECT_MODEL", "ACO-ARCHITECT-MODEL"),
        description="Override model for aco-architect",
    )
    ACO_DEV_MODEL: str | None = Field(
        None,
        validation_alias=AliasChoices("ACO_DEV_MODEL", "ACO-DEV-MODEL"),
        description="Override model for aco-dev",
    )
    ACO_QA_MODEL: str | None = Field(
        None,
        validation_alias=AliasChoices("ACO_QA_MODEL", "ACO-QA-MODEL"),
        description="Override model for aco-qa",
    )
    ACO_HUMAN_MODEL: str | None = Field(
        None,
        validation_alias=AliasChoices("ACO_HUMAN_MODEL", "ACO-HUMAN-MODEL", "ACO_HUMAN"),
        description="Override model for aco-human ('none' to disable the LLM for this agent)",
    )
    
    # Database
    DATABASE_URL: str = Field("sqlite:///./data/aco.db", description="Database connection string")
    
    # Redis (optional)
    REDIS_URL: str | None = Field(None, description="Redis connection string")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_FORMAT: str = Field("json", description="json or text")
    
    # Agent Settings
    AGENT_POLL_INTERVAL_SECONDS: int = Field(30, description="Seconds between agent polls")
    MAX_RETRY_ATTEMPTS: int = Field(3, description="Max retry attempts on failure")
    AGENT_PROMPTS_DIR: str = Field("agent_prompts", description="Directory containing agent prompt markdown files")
    RULES_DIR: str = Field("rules", description="Directory containing rule files")
    SKILLS_DIR: str = Field("skills", description="Directory containing skill files")
    CONTEXTS_DIR: str = Field("contexts", description="Directory containing project context files")
    HOOKS_DIR: str = Field("hooks", description="Directory containing hook JSON configs")

    # Context Management
    MAX_CONTEXT_TOKENS: int = Field(128000, description="Max tokens before context trimming")
    RECENT_COMMENTS_COUNT: int = Field(10, description="Keep this many recent comments unsummarized")
    
    # Human Contact
    HUMAN_CONTACT_METHOD: str = Field("whatsapp", description="How to contact human")
    HUMAN_PHONE: str = Field("+1234567890", description="Human's phone number")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        populate_by_name=True,
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
