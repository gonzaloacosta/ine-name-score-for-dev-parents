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


# Review fixes
@pytest.fixture(scope="module")
def boys():
    return dataset.load(sex=Sex.MALE)


def test_cedilla_names_are_found_in_the_census(boys):
    candidates, census = boys

    result = explain("Llorenç", candidates, census, DEFAULT_WEIGHTS)

    assert result.in_census
    assert result.scored.candidate.census_frequency == census["LLORENÇ"]


@pytest.mark.parametrize("name", ["María José", "maria jose", "Ana-Belén"])
def test_compound_names_are_found_in_the_census(girls, name):
    candidates, census = girls

    assert explain(name, candidates, census, DEFAULT_WEIGHTS).in_census


def test_typed_name_without_accent_uses_the_lexicon_outside_the_pool(girls, boys):
    g_candidates, g_census = girls
    b_candidates, b_census = boys

    monica = explain("Monica", g_candidates, g_census, DEFAULT_WEIGHTS, sex=Sex.FEMALE)
    oscar = explain("oscar", b_candidates, b_census, DEFAULT_WEIGHTS, sex=Sex.MALE)

    assert monica.scored.candidate.written == "Mónica"
    assert monica.spelling_checked
    assert oscar.scored.candidate.written == "Óscar"
    assert oscar.scored.syllables.stress.value == "llana"


def test_unverified_spelling_is_flagged(girls):
    candidates, census = girls

    assert not explain("Zenobia", candidates, census, DEFAULT_WEIGHTS).spelling_checked
    assert explain("Paula", candidates, census, DEFAULT_WEIGHTS).spelling_checked
    assert explain("Begoña", candidates, census, DEFAULT_WEIGHTS).spelling_checked  # typed accent


def test_unknown_name_gets_no_spelling_credit(girls):
    candidates, census = girls

    assert explain("Zzyzx", candidates, census, DEFAULT_WEIGHTS).scored.criteria["spelling"] == 0.0


def test_name_without_vowels_is_rejected(girls):
    candidates, census = girls

    with pytest.raises(ValueError, match="vowel"):
        explain("Brr", candidates, census, DEFAULT_WEIGHTS)


def test_rank_position_respects_surnames(girls):
    candidates, census = girls
    listed = rank(candidates, census, DEFAULT_WEIGHTS, surnames=["Ordo"])
    zoe_position = next(i for i, s in enumerate(listed, 1) if s.candidate.key == "ZOE")

    zoe = explain("Zoe", candidates, census, DEFAULT_WEIGHTS, surnames=["Ordo"])
    gala = explain("Gala", candidates, census, DEFAULT_WEIGHTS, surnames=["Ordo"])

    assert zoe.position == zoe_position
    assert gala.position is None and gala.excluded


@pytest.mark.parametrize(
    ("typed", "written"),
    [("maria de la o", "María de la O"), ("o'neill", "O'Neill"), ("ana-belén", "Ana-Belén")],
)
def test_typed_names_are_capitalised_like_names(girls, typed, written):
    candidates, census = girls

    assert explain(typed, candidates, census, DEFAULT_WEIGHTS).scored.candidate.written == written


def test_cli_explain_rejects_names_without_vowels(capsys):
    assert main(["explain", "Brr"]) == 2
    assert "vowel" in capsys.readouterr().err
