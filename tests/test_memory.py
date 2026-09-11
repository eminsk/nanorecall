"""
Unit Tests for NanoRecall Semantic Memory Engine
"""

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest
from nanorecall.memory import FastFeatureEmbedder, RecallMemory


@pytest.fixture
def temp_memory_dir():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_feature_embedder():
    embedder = FastFeatureEmbedder(dim=128)
    vec1 = embedder.encode("sqlfluff pull request 8449 github")
    vec2 = embedder.encode("sqlfluff pull request 8449 github")
    vec3 = embedder.encode("completely unrelated recipe for chocolate cake")

    assert vec1.shape == (128,)
    # Normalized unit vector
    assert np.isclose(np.linalg.norm(vec1), 1.0, atol=1e-4)

    # Identical texts yield identical vectors
    assert np.allclose(vec1, vec2)

    # Cosine similarity with identical query is 1.0
    sim_match = float(np.dot(vec1, vec2))
    assert np.isclose(sim_match, 1.0, atol=1e-4)

    # Unrelated text has low similarity
    sim_unrelated = float(np.dot(vec1, vec3))
    assert sim_unrelated < 0.3


def test_memory_indexing_and_search(temp_memory_dir):
    mem = RecallMemory(db_dir=temp_memory_dir, embed_dim=128)

    mem.index_frame(
        frame_id="frame_001",
        text="Discussed CV11 fix for StarRocks support in sqlfluff",
        app_name="Google Chrome",
        window_title="sqlfluff #8449 on GitHub",
        image_path="/path/to/frame_001.webp",
        thumb_path="/path/to/thumb_001.webp",
        timestamp="2026-09-11T14:23:00",
    )

    mem.index_frame(
        frame_id="frame_002",
        text="Docker container build failed with segmentation fault on port 8080",
        app_name="Terminal",
        window_title="PowerShell - docker build",
        image_path="/path/to/frame_002.webp",
        thumb_path="/path/to/thumb_002.webp",
        timestamp="2026-09-11T15:10:00",
    )

    mem.index_frame(
        frame_id="frame_003",
        text="Checked weather forecast in New York for weekend trip",
        app_name="Edge",
        window_title="Weather Forecast",
        image_path="/path/to/frame_003.webp",
        thumb_path="/path/to/thumb_003.webp",
        timestamp="2026-09-11T16:00:00",
    )

    # Save to disk
    mem.save()
    assert mem.nvec_file.exists()

    # Search query 1: sqlfluff
    res_sql = mem.search("sqlfluff github pull request", top_k=1)
    assert len(res_sql) == 1
    assert res_sql[0].id == "frame_001"
    assert res_sql[0].app_name == "Google Chrome"

    # Search query 2: docker error
    res_docker = mem.search("docker segmentation fault", top_k=1)
    assert len(res_docker) == 1
    assert res_docker[0].id == "frame_002"
    assert res_docker[0].app_name == "Terminal"

    # Test loading from disk into a fresh instance
    mem2 = RecallMemory(db_dir=temp_memory_dir, embed_dim=128)
    assert len(mem2.index) == 3
    stats = mem2.get_stats()
    assert stats["total_frames"] == 3
    assert stats["vector_dim"] == 128
