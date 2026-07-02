"""Unit tests for dataset mood bucketing (§6.5)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from mood_rules import (  # noqa: E402
    DATASET_MOODS,
    assign_dataset_moods,
    mood_matches,
)


@pytest.mark.parametrize("mood", DATASET_MOODS)
def test_mood_profile_matches(mood: str):
    profiles = {
        "ENERGISED": dict(energy=0.8, valence=0.7, tempo=130, instrumentalness=0.1),
        "FOCUSED": dict(energy=0.45, valence=0.5, tempo=95, instrumentalness=0.7),
        "LOW_KEY": dict(energy=0.2, valence=0.45, tempo=80, instrumentalness=0.2),
        "NOSTALGIC": dict(energy=0.45, valence=0.55, tempo=100, instrumentalness=0.2),
        "SAD": dict(energy=0.2, valence=0.2, tempo=70, instrumentalness=0.1),
    }
    assert mood_matches(profiles[mood], mood)


def test_adventurous_not_in_dataset_moods():
    assert "ADVENTUROUS" not in DATASET_MOODS


def test_untagged_track():
    track = dict(energy=0.55, valence=0.2, tempo=105, instrumentalness=0.3)
    primary, tags = assign_dataset_moods(track)
    assert primary is None
    assert tags == []


def test_multi_mood_overlap():
    track = dict(energy=0.35, valence=0.35, tempo=85, instrumentalness=0.1)
    _, tags = assign_dataset_moods(track)
    assert "LOW_KEY" in tags or "SAD" in tags or "NOSTALGIC" in tags
