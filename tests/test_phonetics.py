import pytest

from name_selector.phonetics import Stress, phonetic_key, syllabify


@pytest.mark.parametrize(
    ("word", "syllables", "stress"),
    [
        ("Julia", 2, Stress.LLANA),
        ("Paula", 2, Stress.LLANA),
        ("Lucía", 3, Stress.LLANA),
        ("María", 3, Stress.LLANA),
        ("Martina", 3, Stress.LLANA),
        ("Valentina", 4, Stress.LLANA),
        ("Inés", 2, Stress.AGUDA),
        ("Isabel", 3, Stress.AGUDA),
        ("Abril", 2, Stress.AGUDA),
        ("Mar", 1, Stress.AGUDA),
        ("Ángela", 3, Stress.ESDRUJULA),
        ("Fátima", 3, Stress.ESDRUJULA),
        ("Naia", 2, Stress.LLANA),
        ("Alaia", 3, Stress.LLANA),
        ("Ainhoa", 3, Stress.LLANA),
        ("Leyre", 2, Stress.LLANA),
        ("Nerea", 3, Stress.LLANA),
        ("Claudia", 2, Stress.LLANA),
        ("Carmen", 2, Stress.LLANA),
        ("Iris", 2, Stress.LLANA),
        ("Mía", 2, Stress.LLANA),
        ("Guiomar", 2, Stress.AGUDA),
    ],
)
def test_syllabify_counts_nuclei_and_places_stress(word, syllables, stress):
    result = syllabify(word)

    assert result.count == syllables
    assert result.stress is stress


def test_syllabify_reports_vowel_ending():
    assert syllabify("Julia").ends_in_vowel
    assert not syllabify("Carmen").ends_in_vowel


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("EMMA", "EMA"),
        ("SARA", "SARAH"),
        ("ELENA", "HELENA"),
        ("VALERIA", "BALERIA"),
        ("LEIRE", "LEYRE"),
        ("CHLOE", "CLOE"),
        ("CLOE", "KLOE"),
        ("NOA", "NOAH"),
        ("JIMENA", "GIMENA"),
        ("ISABEL", "YSABEL"),
        ("ISABEL", "IZABEL"),
        ("LUCIA", "LUCÍA"),
        ("NAIA", "NAHIA"),
    ],
)
def test_phonetic_key_merges_homophone_spellings(a, b):
    assert phonetic_key(a) == phonetic_key(b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("LUCIA", "LUISA"),
        ("JULIA", "JULIETA"),
        ("GUIOMAR", "JIOMAR"),
        ("MARIA", "MARINA"),
    ],
)
def test_phonetic_key_keeps_distinct_names_apart(a, b):
    assert phonetic_key(a) != phonetic_key(b)
