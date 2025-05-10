from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.models.ollama import Ollama
from agno.models.google import Gemini

class ModelProvider:
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"

def get_model_client(provider: str, model_name: str, end_point: str = None, api_key: str = None, max_tokens=10):

    if provider == ModelProvider.OLLAMA:
        return Ollama(
            id=model_name,
        )
    elif provider == ModelProvider.OPENAI:
        if not api_key: 
            raise ValueError("You didn't add correct API key")
        return OpenAIChat(
            id=model_name,
            api_key=api_key,
        )
    elif provider == ModelProvider.GEMINI:
        if not api_key:
            raise ValueError("You didn't add correct API key for Gemini")
        return Gemini(
            id=model_name,
            api_key=api_key,
        )
    elif provider == ModelProvider.ANTHROPIC:
        if not api_key: 
            raise ValueError("You didn't add correct API key")
        return Claude(
            id=model_name,
            api_key=api_key,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
