from __future__ import annotations

from core.config import Settings, normalized_provider, require_llm_credentials


def build_llm(settings: Settings, temperature: float = 0.0):
    provider = normalized_provider(settings)
    require_llm_credentials(settings)

    if provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "langchain-google-genai is required for the Gemini provider. "
                "Install it with: uv sync --extra google"
            ) from None

        return ChatGoogleGenerativeAI(
            model=settings.model_name,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )
    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "langchain-openai is required for the OpenAI provider. "
                "Install it with: uv sync --extra openai"
            ) from None

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            temperature=temperature,
        )
    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "langchain-anthropic is required for the Anthropic provider. "
                "Install it with: uv sync --extra anthropic"
            ) from None

        return ChatAnthropic(
            model=settings.model_name,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
        )
    if provider == "openrouter":
        try:
            from langchain_openai import ChatOpenAI  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "langchain-openai is required for the OpenRouter provider. "
                "Install it with: uv sync --extra openai"
            ) from None

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=temperature,
        )
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "langchain-ollama is required for the Ollama provider. "
                "Install it with: uv sync --extra ollama"
            ) from None

        return ChatOllama(
            model=settings.model_name,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )
    if provider == "custom":
        try:
            from langchain_openai import ChatOpenAI  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "langchain-openai is required for custom OpenAI-compatible providers. "
                "Install it with: uv sync --extra openai"
            ) from None

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.custom_llm_api_key or "unused",
            base_url=settings.custom_llm_base_url,
            temperature=temperature,
        )
    if provider == "nvidia":
        try:
            from langchain_openai import ChatOpenAI  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "langchain-openai is required for the NVIDIA provider. "
                "Install it with: uv sync --extra openai"
            ) from None

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            temperature=temperature,
        )
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
