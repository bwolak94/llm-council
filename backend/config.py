"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Default council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

# Default chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Models available for selection in the UI
AVAILABLE_MODELS = [
    "openai/gpt-5.1",
    "openai/gpt-4.1",
    "openai/gpt-4o",
    "google/gemini-3-pro-preview",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "anthropic/claude-opus-4",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-haiku-4-5",
    "x-ai/grok-4",
    "x-ai/grok-3",
    "meta-llama/llama-4-maverick",
    "deepseek/deepseek-r1",
]

# Runtime overrides (changed via /api/config, reset on server restart)
_runtime_council_models = None
_runtime_chairman_model = None


def get_council_models():
    return _runtime_council_models if _runtime_council_models is not None else COUNCIL_MODELS


def get_chairman_model():
    return _runtime_chairman_model if _runtime_chairman_model is not None else CHAIRMAN_MODEL


def set_council_models(models):
    global _runtime_council_models
    _runtime_council_models = models


def set_chairman_model(model):
    global _runtime_chairman_model
    _runtime_chairman_model = model
