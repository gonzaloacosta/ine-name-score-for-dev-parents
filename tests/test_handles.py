from name_selector.handles import Tier, find_bad_handles, generate_handles, slug


def test_slug_strips_accents_enye_spaces_and_case():
    assert slug("Begoña") == "begona"
    assert slug("de la Fuente") == "delafuente"
    assert slug("López-Ruiz") == "lopezruiz"


def test_generate_handles_covers_common_email_patterns():
    handles = {h.text for h in generate_handles("Gonzalo", ["Ordo", "López"])}

    assert {"gordo", "gonzaloordo", "ordogonzalo", "gonzaloo", "gordol", "gordolopez"} <= handles
    assert "gol" in handles  # initials


def test_initial_plus_surname_spelling_a_negative_word_is_flagged():
    hits = find_bad_handles("Gonzalo", ["Ordo"])

    assert [(h.handle, h.word, h.tier) for h in hits if h.handle == "gordo"] == [
        ("gordo", "gordo", Tier.NEGATIVE),
    ]


def test_offensive_word_is_flagged_anywhere_across_name_and_surname():
    hits = find_bad_handles("Ana", ["López"])

    assert any(h.handle == "analopez" and h.word == "anal" for h in hits)


def test_negative_word_only_counts_at_handle_edges():
    # "almalopez" hides "malo" mid-handle: not how anyone would read it.
    assert not any(h.word == "malo" for h in find_bad_handles("Alma", ["López"]))
    # "l" + "ocaña" -> "locana" starts with "loca".
    assert any(h.word == "loca" for h in find_bad_handles("Lucía", ["Ocaña"]))


def test_word_entirely_inside_the_surname_is_not_blamed_on_the_name():
    assert find_bad_handles("Julia", ["Gordo"]) == []


def test_clean_combination_has_no_hits():
    assert find_bad_handles("Julia", ["García", "Martín"]) == []


def test_negative_word_inside_the_name_alone_is_not_flagged():
    # "fatimalopez" starts with "fat", but nobody reads Fátima as "fat".
    assert not any(h.word == "fat" for h in find_bad_handles("Fátima", ["López"]))
