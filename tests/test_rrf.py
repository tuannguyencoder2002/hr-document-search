"""Unit tests for RRF fusion."""

from __future__ import annotations

from src.search.retriever import rrf_fusion


def test_rrf_single_list():
    fused = rrf_fusion([[("a", 0), ("b", 1), ("c", 2)]], k=60)
    ids = [doc for doc, _ in fused]
    assert ids == ["a", "b", "c"]


def test_rrf_merges_two_lists():
    # "b" appears at rank 1 in list 1 and rank 0 in list 2 -> should be #1.
    dense = [("a", 0), ("b", 1), ("c", 2)]
    sparse = [("b", 0), ("a", 1), ("d", 2)]
    fused = rrf_fusion([dense, sparse], k=60)
    ids = [doc for doc, _ in fused]
    assert ids[0] in {"a", "b"}
    # "a" and "b" should both beat "c" and "d"
    top2 = set(ids[:2])
    assert top2 == {"a", "b"}


def test_rrf_score_monotonic():
    fused = rrf_fusion([[("x", 0), ("y", 1), ("z", 2)]], k=60)
    scores = [score for _, score in fused]
    assert scores == sorted(scores, reverse=True)


def test_rrf_empty_lists_returns_empty():
    assert rrf_fusion([], k=60) == []
    assert rrf_fusion([[], []], k=60) == []
