"""
Persistent answer key store - saved once, reused forever.
Stored at data/answer_key.json
"""
import json
from pathlib import Path

_KEY_FILE = Path("data/answer_key.json")
_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)


def save(answer_key: dict):
    """Save answer key permanently. {q_num(int): option_letter(str)}"""
    _KEY_FILE.write_text(json.dumps(answer_key, indent=2))


def load() -> dict:
    """Load saved answer key. Returns {} if not saved yet."""
    if not _KEY_FILE.exists():
        return {}
    return json.loads(_KEY_FILE.read_text())


def exists() -> bool:
    return _KEY_FILE.exists() and bool(load())
