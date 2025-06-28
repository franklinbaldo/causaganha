import logging
from typing import List, Dict

try:
    from langdetect import detect
except Exception:  # pragma: no cover - library not available
    detect = None  # type: ignore
    logging.warning("langdetect not installed; language detection disabled")

try:
    from googletrans import Translator  # type: ignore
except Exception:  # pragma: no cover - library not available
    Translator = None  # type: ignore
    logging.warning("googletrans not installed; translation disabled")


def detect_language(text: str) -> str:
    """Detect language for a given text."""
    if not detect:
        return "unknown"
    try:
        lang = detect(text)
        if lang in {"pt", "es"}:
            return lang
    except Exception:
        pass
    return "unknown"


def translate_text(text: str, target_lang: str = "pt") -> str:
    """Translate text to target language if translator available."""
    if Translator:
        try:
            translator = Translator()
            result = translator.translate(text, dest=target_lang)
            return result.text
        except Exception:
            pass
    # Fallback simple dictionary
    fallback = {
        "hola": "olá",
        "rechazado": "rejeitado",
        "aprobado": "aprovado",
    }
    return fallback.get(text.lower(), text)


def evaluate_cross_lingual(decisions: List[Dict]) -> Dict[str, int]:
    """Simple count of decisions per detected language."""
    stats: Dict[str, int] = {"pt": 0, "es": 0, "unknown": 0}
    for dec in decisions:
        lang = dec.get("language", "unknown")
        if lang not in stats:
            stats[lang] = 0
        stats[lang] += 1
    return stats
