"""
NanoRecall Semantic Episodic Memory Engine
Powered by NanoVector (C99 AVX2 / NEON / FASM)
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import numpy as np
except (ImportError, ModuleNotFoundError):
    np = None

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
    Supports both NumPy vectorized and pure-Python zero-dependency execution.
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def encode(self, text: str) -> Any:
        if np is not None:
            vec = np.zeros(self.dim, dtype=np.float32)
        else:
            vec = [0.0] * self.dim

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

        from nanorecall.fasm import default_engine, is_fasm_available

        if is_fasm_available():
            default_engine.vector_normalize(vec)
            return vec

        if np is not None and hasattr(vec, "dtype"):
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec = vec / norm
        else:
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]
        return vec


class FallbackIndex:
    """Pure-Python / FASM hardware index when NanoVector binary extension is loading."""

    def __init__(self, dim: int, metric: str = "cosine"):
        self.dim = dim
        self.metric = metric
        self.ids: List[str] = []
        self.vectors: List[Any] = []
        self.metas: List[str] = []

    def __len__(self) -> int:
        return len(self.ids)

    def add(self, id: str, vector: Any, metadata: Optional[str] = None) -> None:
        self.ids.append(id)
        if np is not None and hasattr(vector, "astype"):
            self.vectors.append(vector.astype(np.float32))
        elif hasattr(vector, "tolist"):
            self.vectors.append(vector.tolist())
        else:
            self.vectors.append([float(x) for x in vector])
        self.metas.append(metadata or "{}")

    def search(self, query: Any, top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Any]:
        if not self.ids:
            return []

        from nanorecall.fasm import default_engine, is_fasm_available

        q_list = query.tolist() if hasattr(query, "tolist") else list(query)
        if is_fasm_available():
            scores_list = default_engine.batch_search_cosine(q_list, self.vectors)
        elif np is not None and hasattr(query, "astype") and self.vectors and hasattr(self.vectors[0], "dtype"):
            mat = np.array(self.vectors, dtype=np.float32)
            q = query.astype(np.float32)
            scores = np.dot(mat, q)
            scores_list = scores.tolist() if hasattr(scores, "tolist") else list(scores)
        else:
            scores_list = [sum(a * b for a, b in zip(v, q_list)) for v in self.vectors]
        indices = sorted(range(len(scores_list)), key=lambda i: scores_list[i], reverse=True)
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

            results.append(SimpleMatch(self.ids[idx], scores_list[idx], meta_str))
            if len(results) >= top_k:
                break
        return results

    def save(self, path: str) -> None:
        data = {
            "dim": self.dim,
            "ids": self.ids,
            "vectors": [v.tolist() if hasattr(v, "tolist") else list(v) for v in self.vectors],
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
        idx.vectors = [np.array(v, dtype=np.float32) if np is not None else [float(x) for x in v] for v in data["vectors"]]
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

    def encode_text(self, text: str) -> Any:
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
