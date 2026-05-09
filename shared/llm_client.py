from __future__ import annotations

import logging
from typing import Any, Optional
from google import genai
from google.genai import types

from shared.settings import GEMINI_API_KEY, LLM_TEMPERATURE
from shared.retry_utils import retry_on_transient_errors

logger = logging.getLogger(__name__)

_MIN_TEMPERATURE = 0.0
_MAX_TEMPERATURE = 2.0


def _sanitize_temperature(temperature: Optional[float]) -> float:
    resolved_temperature = temperature if temperature is not None else LLM_TEMPERATURE
    clamped_temperature = max(_MIN_TEMPERATURE, min(_MAX_TEMPERATURE, float(resolved_temperature)))

    if clamped_temperature != resolved_temperature:
        logger.warning(
            "Temperature %.3f is outside Gemini's supported range %.1f-%.1f; clamping to %.3f.",
            resolved_temperature,
            _MIN_TEMPERATURE,
            _MAX_TEMPERATURE,
            clamped_temperature,
        )

    return clamped_temperature

class LLMClient:
    """
    Production-quality reusable Gemini client.
    Handles initialization, error handling, and structured logging.
    """
    _instance: Optional[genai.Client] = None

    @classmethod
    def get_client(cls) -> genai.Client:
        if cls._instance is None:
            if not GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY is not set in environment")
                raise ValueError("GEMINI_API_KEY is required")
            
            try:
                cls._instance = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("Gemini Client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
                raise

        return cls._instance

    @classmethod
    @retry_on_transient_errors()
    def generate_content(
        cls, 
        model: str, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        response_mime_type: str = "text/plain"
    ) -> str:
        client = cls.get_client()
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=_sanitize_temperature(temperature),
            response_mime_type=response_mime_type
        )

        try:
            logger.info(f"Executing prompt on model: {model}")
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            
            if not response or not response.text:
                logger.warning(f"Empty response from model {model}")
                return ""
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"API failure during content generation on {model}: {e}")
            # Here you could implement fallback logic or re-raise
            raise

def get_llm_client() -> genai.Client:
    return LLMClient.get_client()
