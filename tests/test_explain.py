import pytest

from name_selector import dataset
from name_selector.cli import main
from name_selector.models import Sex
from name_selector.scoring import DEFAULT_WEIGHTS, explain, rank


@pytest.fixture(scope="module")
def girls():
    return dataset.load(sex=Sex.FEMALE)


def test_pool_name_matches_its_ranking_entry(girls):
    candidates, census = girls
    ranked = rank(candidates, census, DEFAULT_WEIGHTS)

    result = explain("Paula", candidates, census, DEFAULT_WEIGHTS)

    assert result.position == 1
    assert result.pool_size == len(ranked)
    assert result.scored.total == ranked[0].total


def test_name_typed_without_accent_uses_the_curated_spelling(girls):
    candidates, census = girls

    result = explain("lucia", candidates, census, DEFAULT_WEIGHTS)

    assert result.scored.candidate.written == "Lucía"
    assert result.position is not None


def test_census_name_outside_the_top_100_is_scored_with_the_typed_spelling(girls):
    candidates, census = girls

    result = explain("begoña", candidates, census, DEFAULT_WEIGHTS)

    assert result.position is None
    assert result.in_census
    assert result.scored.candidate.written == "Begoña"
    assert result.scored.candidate.census_frequency == census["BEGOÑA"]
    assert result.scored.criteria["ascii"] == 0.0
    assert 0.0 <= result.scored.total <= 1.0


def test_unknown_name_scores_zero_anonymity(girls):
    candidates, census = girls

    result = explain("Zzyzx", candidates, census, DEFAULT_WEIGHTS)

    assert not result.in_census
    assert result.scored.criteria["anonymity"] == 0.0
    assert result.scored.criteria["current"] == 0.0


def test_mean_age_is_available_outside_the_pool():
    ages = dataset.load_ages(sex=Sex.FEMALE)

    assert ages["BEGOÑA"] > 40


def test_cli_explain_supports_boys_and_names_outside_the_pool(capsys):
    assert main(["--sex", "male", "explain", "hugo"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Hugo")
    assert "#4 of" in out

    assert main(["explain", "Begoña"]) == 0
    assert "not in the INE newborn top-100" in capsys.readouterr().out


def test_cli_rank_for_boys(capsys):
    assert main(["--sex", "male", "rank", "--top", "3"]) == 0
    assert "Pablo" in capsys.readouterr().out
