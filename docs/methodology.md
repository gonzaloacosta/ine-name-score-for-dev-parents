# Methodology

Each candidate gets six scores in [0, 1]. The total is their weighted average.

| Criterion | Default weight | How it is computed |
|---|---|---|
| `anonymity` | 0.25 | log-scaled number of women in Spain with this exact simple name (census), min–max over the pool. More namesakes = harder to single out. |
| `ascii` | 0.20 | 1 if the written form is plain A–Z, else 0. Accents/ñ get mangled or stripped by airline, bank and foreign systems, which creates identity mismatches. |
| `song` | 0.20 | Syllables {2,3: 1.0, 4: 0.6, 1: 0.4, 5+: 0.3} × stress {llana 1.0, aguda 0.6, esdrújula 0.4} × (0.85 if it ends in a consonant). |
| `spelling` | 0.15 | Share of census women with this *sound* who use this *spelling* (e.g. Helena vs Elena → 0.11), × 0.85 if it has non-native graphemes (k, w, double letters, final y, chl…). |
| `current` | 0.10 | log-scaled mean newborn count across loaded years, min–max over the pool. |
| `systems` | 0.10 | 0 for reserved words (`Null`, `Test`…); penalties for spaces/hyphens, < 3 or > 12 chars. |

## Why the song rule

In the third line of *Cumpleaños feliz* the name sits on the melody's climax: the strong beat
falls on its penultimate syllable and the last syllable is a held note. That favours *llanas*
of 2–3 syllables ending in a vowel (*JU-lia*, *Mar-TI-na*).

## Sound-alike key

`phonetics.phonetic_key` merges spellings Spanish speakers can't tell apart: b/v, silent h,
y/i/ll, seseo (c/z/s), c/k/qu, g/j before e/i, doubled letters, ph/th/sh.

## Email / username filter (`--surnames`)

Not a weighted criterion but a hard filter: a name is dropped when any generated handle
spells a listed word. Handles are lowercase a–z (accents and ñ stripped, separators dropped
because `ana.lopez` still reads `analopez`) built from these patterns, with n = name,
s1/s2 = surnames:

`n+s1`, `n[0]+s1`, `n+s1[0]`, `s1+n`, `s1+n[0]` and, with two surnames, `n+s1+s2`,
`n[0]+s1+s2`, `n[0]+s1+s2[0]`, `n+s2`, initials.

Words live in `name_selector/wordlists/` (Spanish + English, one per line):

- `offensive.txt`: flagged anywhere, if the match touches the name (`ana|lopez` -> anal).
- `negative.txt`: teasing words, flagged only at the start/end of the handle and only when
  the combination creates them (`g|ordo` -> gordo) or they are the whole name. Fátima is not
  flagged for "fat".

Words entirely inside a surname are ignored: they affect every name equally.

## Known limitations

- INE publishes names without accents, so `lexicon.py` stores the correct spelling for
  accented names in the pool (Lucía, Inés…) and overrides pronunciation where Spanish rules
  misread it (Mia → Mía, Chloe → Cloe). New names from future years may need entries there.
- `anonymity` and `current` are relative to the pool, so `--ascii-only` shifts them slightly.
- Only the national top-100 per year is published, so names outside it are not candidates.
- The word lists are curated, not exhaustive: extend them for your own surnames' risks.
  Leetspeak and phonetic matches (`kaka`) are not detected.
- Real-world findability depends mostly on the full name with both surnames, which this tool
  cannot see.
