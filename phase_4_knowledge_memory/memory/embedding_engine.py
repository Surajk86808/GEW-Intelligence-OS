from __future__ import annotations

import hashlib
import math
from typing import Any

from .config import EMBEDDING_CACHE_PATH, EMBEDDING_DIMENSION, EMBEDDING_PROVIDER
from shared.json_utils import read_json, write_json


class EmbeddingEngine:
    def __init__(self) -> None:
        self.cache = read_json(EMBEDDING_CACHE_PATH, default={}) or {}

    def embed_text(self, text: str) -> list[float]:
        if EMBEDDING_PROVIDER != "hashing":
            raise RuntimeError(f"Embedding provider '{EMBEDDING_PROVIDER}' is not implemented yet.")

        cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]

        vector = [0.0] * EMBEDDING_DIMENSION
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            token_hash = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(token_hash[:4], "big") % EMBEDDING_DIMENSION
            sign = -1.0 if token_hash[4] % 2 else 1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [round(value / norm, 8) for value in vector]

        self.cache[cache_key] = vector
        return vector

    def persist_cache(self) -> None:
        write_json(EMBEDDING_CACHE_PATH, self.cache)

    def _tokenize(self, text: str) -> list[str]:
        cleaned = "".join(char.lower() if char.isalnum() else " " for char in text)
        return [token for token in cleaned.split() if token]
