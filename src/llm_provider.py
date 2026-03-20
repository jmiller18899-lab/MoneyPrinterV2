import ollama
from openai import OpenAI

from config import (
    get_ollama_base_url,
    get_openrouter_api_key,
    get_openrouter_model,
)

_selected_model: str | None = None

_OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemma-3-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
]


def _use_openrouter() -> bool:
    return bool(get_openrouter_api_key())


def _openrouter_client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=get_openrouter_api_key(),
    )


def _ollama_client() -> ollama.Client:
    return ollama.Client(host=get_ollama_base_url())


def list_models() -> list[str]:
    """
    Lists available models.

    When OpenRouter is configured, returns a list of recommended free models.
    Otherwise lists models available on the local Ollama server.

    Returns:
        models (list[str]): Sorted list of model names.
    """
    if _use_openrouter():
        return _OPENROUTER_FREE_MODELS
    response = _ollama_client().list()
    return sorted(m.model for m in response.models)


def select_model(model: str) -> None:
    """
    Sets the model to use for all subsequent generate_text calls.

    Args:
        model (str): A model name.
    """
    global _selected_model
    _selected_model = model


def get_active_model() -> str | None:
    """
    Returns the currently selected model, or None if none has been selected.
    """
    return _selected_model


def generate_text(prompt: str, model_name: str = None) -> str:
    """
    Generates text using OpenRouter (if configured) or the local Ollama server.

    Args:
        prompt (str): User prompt
        model_name (str): Optional model name override

    Returns:
        response (str): Generated text
    """
    model = model_name or _selected_model

    if _use_openrouter():
        if not model:
            model = get_openrouter_model()
        response = _openrouter_client().chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    if not model:
        raise RuntimeError(
            "No model selected. Call select_model() first or pass model_name."
        )
    response = _ollama_client().chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()
