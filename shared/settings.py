from __future__ import annotations

from shared.config_utils import get_env, get_env_float

# Gemini API Configuration
GEMINI_API_KEY = get_env("GEMINI_API_KEY", "")

# Model Routing
# Lightweight operations (e.g., classification, simple summaries)
QUERY_MODEL = get_env("QUERY_MODEL", "gemini-2.5-flash")

# Deep reasoning / synthesis (e.g., complex analysis, report generation)
REASONING_MODEL = get_env("REASONING_MODEL", "gemini-2.5-pro")

# Legacy/Fallback support
PRIMARY_LLM_MODEL = get_env("PRIMARY_LLM_MODEL", REASONING_MODEL)

# LLM Parameters
LLM_TEMPERATURE = get_env_float("LLM_TEMPERATURE", 0.1)
LLM_TOP_P = get_env_float("LLM_TOP_P", 0.95)
LLM_TOP_K = get_env_float("LLM_TOP_K", 40)

# Provider Configuration
LLM_PROVIDER = get_env("LLM_PROVIDER", "gemini").lower()
