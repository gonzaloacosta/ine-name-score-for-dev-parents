import pytest

from name_selector.models import Candidate
from name_selector.phonetics import syllabify
from name_selector.scoring import (
    DEFAULT_WEIGHTS,
    ascii_score,
    log_scale,
    parse_weights,
    rank,
    song_score,
    spelling_score,
    systems_score,
)


def make_candidate(key, written=None, pronunciation=None, census=10_000, births=500):
    written = written or key.title()
    return Candidate(
        key=key,
        written=written,
        pronunciation=pronunciation or written,
        census_frequency=census,
        census_mean_age=10.0,
        births={2024: births},
    )


def test_ascii_score_rejects_diacritics():
    assert ascii_score("Julia") == 1.0
    assert ascii_score("Lucía") == 0.0
    assert ascii_score("Begoña") == 0.0


def test_systems_score_flags_reserved_words_and_bad_lengths():
    assert systems_score("Julia") == 1.0
    assert systems_score("Null") == 0.0
    assert systems_score("Al") < 1.0
    assert systems_score("Maria-Jose") < 1.0
    assert systems_score("Maria Jose") < 1.0


def test_song_score_prefers_two_or_three_syllable_llanas_ending_in_vowel():
    julia = song_score(syllabify("Julia"))
    martina = song_score(syllabify("Martina"))
    carmen = song_score(syllabify("Carmen"))
    ines = song_score(syllabify("Inés"))
    angela = song_score(syllabify("Ángela"))
    valentina = song_score(syllabify("Valentina"))

    assert julia == martina == 1.0
    assert 1.0 > carmen > ines
    assert ines > angela
    assert 1.0 > valentina


def test_spelling_score_is_share_of_people_using_this_spelling():
    census = {"EMMA": 900, "EMA": 100, "JULIA": 1000}

    assert spelling_score("JULIA", census) == pytest.approx(1.0)
    assert spelling_score("EMMA", census) == pytest.approx(0.9 * 0.85)  # share x double letter
    assert spelling_score("EMA", census) == pytest.approx(0.1)


def test_spelling_score_penalises_foreign_graphemes():
    assert spelling_score("CHLOE", {"CHLOE": 100}) < 1.0
    assert spelling_score("YASMIN", {"YASMIN": 100}) == pytest.approx(1.0)


def test_log_scale_maps_range_to_unit_interval():
    assert log_scale(10, 10, 1000) == 0.0
    assert log_scale(1000, 10, 1000) == 1.0
    assert log_scale(100, 10, 1000) == pytest.approx(0.5)
    assert log_scale(5, 5, 5) == 1.0


def test_parse_weights_overrides_defaults_and_rejects_unknown_keys():
    weights = parse_weights("song=0.5,ascii=0")

    assert weights["song"] == 0.5
    assert weights["ascii"] == 0.0
    assert weights["anonymity"] == DEFAULT_WEIGHTS["anonymity"]
    with pytest.raises(ValueError, match="unknown criterion"):
        parse_weights("beauty=1")
    with pytest.raises(ValueError, match="must be >= 0"):
        parse_weights("song=-1")


def test_rank_orders_by_weighted_total_and_can_filter_non_ascii():
    candidates = [
        make_candidate("JULIA", census=200_000, births=2000),
        make_candidate("LUCIA", written="Lucía", census=200_000, births=2800),
        make_candidate("ZENOBIA", census=500, births=10),
    ]
    census = {"JULIA": 200_000, "LUCIA": 200_000, "ZENOBIA": 500}

    ranked = rank(candidates, census, DEFAULT_WEIGHTS)
    ascii_only = rank(candidates, census, DEFAULT_WEIGHTS, ascii_only=True)

    assert [r.candidate.key for r in ranked][0] == "JULIA"
    assert ranked[-1].candidate.key == "ZENOBIA"
    assert "LUCIA" not in [r.candidate.key for r in ascii_only]
    assert all(0.0 <= r.total <= 1.0 for r in ranked)
