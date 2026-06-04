"""Robust .env loading. Handles BOM-prefixed files and stray quotes."""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, find_dotenv


def load_config(env_path: Optional[Path] = None) -> dict:
    """Load Azure credentials and config from a .env file.

    Manually parses the file with utf-8-sig (which strips a BOM that
    Notepad often adds) and tolerates stray quotes/spaces around values.

    Returns a dict with all keys downstream modules expect.
    """
    if env_path is None:
        found = find_dotenv()
        env_path = Path(found) if found else None
    elif isinstance(env_path, str):
        env_path = Path(env_path)

    if not env_path or not env_path.exists():
        raise FileNotFoundError(
            "No .env file found. Pass env_path explicitly or place .env "
            "next to your notebook."
        )

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
    load_dotenv(env_path, override=False)

    return {
        "azure_openai_endpoint":    _require("AZURE_OPENAI_ENDPOINT"),
        "azure_openai_api_key":     _require("AZURE_OPENAI_API_KEY"),
        "azure_openai_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        "chat_deployment":          os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o"),
        "embedding_deployment":     os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        "search_endpoint":          _require("AZURE_SEARCH_ENDPOINT"),
        "search_api_key":           _require("AZURE_SEARCH_API_KEY"),
    }


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value
