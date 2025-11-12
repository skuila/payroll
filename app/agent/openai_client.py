# agent/openai_client.py — Client OpenAI sécurisé (clé via variable d'environnement)
import os
from openai import OpenAI


def _resolve_key() -> str:
    k = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not k:
        raise RuntimeError(
            'Clé API manquante. Définis OPENAI_API_KEY dans l\'environnement Windows: setx OPENAI_API_KEY "ta_cle"'
        )
    return k


_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=_resolve_key())
    return _client


def ask_text(prompt: str, model: str = "gpt-4o-mini") -> str:
    client = get_client()
    r = client.responses.create(
        model=model,
        instructions="Assistant paie/compta. Réponds en français, clair et concis.",
        input=prompt,
    )
    return getattr(r, "output_text", "").strip() or str(r)
