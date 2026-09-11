"""
NanoRecall Semantic Episodic Memory Engine
Powered by NanoVector (C99 AVX2 / NEON / FASM)
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

try:
    import nanovector
    from nanovector import Index, Match
except ImportError:
    # Graceful local fallback or wrapper for development/standalone environments
    nanovector = None
    Index = None
    Match = None


@dataclass
class MemoryMatch:
    id: str
    score: float
    timestamp: str
    app_name: str
    window_title: str
    image_path: str
    thumb_path: str
    snippet: str

    @classmethod
    def from_dict(cls, id: str, score: float, meta: Dict[str, Any]) -> "MemoryMatch":
        return cls(
            id=id,
            score=score,
            timestamp=meta.get("timestamp", ""),
            app_name=meta.get("app_name", "Unknown"),
            window_title=meta.get("window_title", ""),
            image_path=meta.get("image_path", ""),
            thumb_path=meta.get("thumb_path", ""),
            snippet=meta.get("snippet", ""),
        )


class FastFeatureEmbedder:
    """
    Zero-dependency, microsecond subword & token feature hasher.
    Maps text to normalized unit vectors without downloading heavy neural models.
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def encode(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        if not text:
            return vec

        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return vec

        for tok in tokens:
            # Word hash
            h_word = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[h_word] += 1.0

            # 3-char subword n-grams for typo-tolerant fuzzy matching
            if len(tok) >= 3:
                for i in range(len(tok) - 2):
                    ngram = tok[i : i + 3]
                    h_ng = int(hashlib.sha1(ngram.encode("utf-8")).hexdigest(), 16) % self.dim
                    vec[h_ng] += 0.5

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec


class FallbackIndex:
    """Pure-Python fallback index when NanoVector binary extension is loading."""

    def __init__(self, dim: int, metric: str = "cosine"):
        self.dim = dim
        self.metric = metric
        self.ids: List[str] = []
        self.vectors: List[np.ndarray] = []
        self.metas: List[str] = []

    def __len__(self) -> int:
        return len(self.ids)

    def add(self, id: str, vector: np.ndarray, metadata: Optional[str] = None) -> None:
        self.ids.append(id)
        self.vectors.append(vector.astype(np.float32))
        self.metas.append(metadata or "{}")

    def search(self, query: np.ndarray, top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Any]:
        if not self.ids:
            return []
        mat = np.array(self.vectors, dtype=np.float32)
        q = query.astype(np.float32)
        scores = np.dot(mat, q)

        indices = np.argsort(-scores)
        results = []
        for idx in indices:
            meta_str = self.metas[idx]
            try:
                meta_dict = json.loads(meta_str)
            except Exception:
                meta_dict = {}

            if filter:
                match = True
                for k, v in filter.items():
                    if meta_dict.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            class SimpleMatch:
                def __init__(self, id, score, metadata):
                    self.id = id
                    self.score = float(score)
                    self.metadata = metadata

            results.append(SimpleMatch(self.ids[idx], scores[idx], meta_str))
            if len(results) >= top_k:
                break
        return results

    def save(self, path: str) -> None:
        data = {
            "dim": self.dim,
            "ids": self.ids,
            "vectors": [v.tolist() for v in self.vectors],
            "metas": self.metas,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str) -> "FallbackIndex":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        idx = cls(dim=data["dim"])
        idx.ids = data["ids"]
        idx.vectors = [np.array(v, dtype=np.float32) for v in data["vectors"]]
        idx.metas = data["metas"]
        return idx


class RecallMemory:
    """
    Episodic memory store managing screen snapshots, OCR text, and semantic vectors.
    """

    def __init__(
        self,
        db_dir: Optional[Path] = None,
        embed_dim: int = 128,
        use_neural: bool = False,
    ):
        if db_dir is None:
            self.db_dir = Path.home() / ".nanorecall"
        else:
            self.db_dir = Path(db_dir)

        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.nvec_file = self.db_dir / "memory.nvec"
        self.embed_dim = embed_dim
        self.use_neural = use_neural

        self.embedder: Any = None
        if self.use_neural:
            try:
                from sentence_transformers import SentenceTransformer
                self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
                self.embed_dim = 384
            except Exception:
                self.embedder = FastFeatureEmbedder(dim=self.embed_dim)
        else:
            self.embedder = FastFeatureEmbedder(dim=self.embed_dim)

        self.index = self._load_or_create_index()

    def _load_or_create_index(self) -> Any:
        if self.nvec_file.exists():
            try:
                if nanovector is not None:
                    return nanovector.load(str(self.nvec_file))
                else:
                    return FallbackIndex.load(str(self.nvec_file))
            except Exception:
                pass

        if nanovector is not None:
            return Index(dim=self.embed_dim, metric="cosine")
        return FallbackIndex(dim=self.embed_dim, metric="cosine")

    def encode_text(self, text: str) -> np.ndarray:
        if self.use_neural and hasattr(self.embedder, "encode"):
            return self.embedder.encode([text], normalize_embeddings=True, show_progress_bar=False)[0].astype(np.float32)
        return self.embedder.encode(text)

    def index_frame(
        self,
        frame_id: str,
        text: str,
        app_name: str = "Unknown",
        window_title: str = "",
        image_path: str = "",
        thumb_path: str = "",
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Extracts vector representation, attaches metadata, and stores into the index.
        """
        if not text and not window_title:
            return

        combined_text = f"{window_title} {app_name} {text}".strip()
        vec = self.encode_text(combined_text)

        if not timestamp:
            timestamp = datetime.now().isoformat()

        # Build clean snippet (first 160 chars)
        snippet = " ".join(text.split())[:160]

        meta = {
            "timestamp": timestamp,
            "app_name": app_name,
            "window_title": window_title,
            "image_path": image_path,
            "thumb_path": thumb_path,
            "snippet": snippet,
        }

        self.index.add(id=frame_id, vector=vec, metadata=json.dumps(meta, ensure_ascii=False))

    def save(self) -> None:
        self.index.save(str(self.nvec_file))

    def search(
        self,
        query: str,
        top_k: int = 10,
        app_filter: Optional[str] = None,
    ) -> List[MemoryMatch]:
        """
        Executes semantic vector search and converts results to MemoryMatch objects.
        """
        if len(self.index) == 0 or not query.strip():
            return []

        q_vec = self.encode_text(query)

        filter_dict = None
        if app_filter:
            filter_dict = {"app_name": app_filter}

        matches = self.index.search(q_vec, top_k=top_k, filter=filter_dict)

        results: List[MemoryMatch] = []
        for m in matches:
            meta_dict = {}
            if hasattr(m, "meta") and isinstance(m.meta, dict):
                meta_dict = m.meta
            elif m.metadata:
                try:
                    meta_dict = json.loads(m.metadata)
                except Exception:
                    pass
            results.append(MemoryMatch.from_dict(id=m.id, score=m.score, meta=meta_dict))

        return results

    def get_stats(self) -> Dict[str, Any]:
        file_size_kb = 0.0
        if self.nvec_file.exists():
            file_size_kb = self.nvec_file.stat().st_size / 1024.0

        return {
            "total_frames": len(self.index),
            "vector_dim": self.embed_dim,
            "backend": "NanoVector (AVX2)" if nanovector is not None else "Fallback",
            "file_size_kb": round(file_size_kb, 2),
            "file_path": str(self.nvec_file),
        }
