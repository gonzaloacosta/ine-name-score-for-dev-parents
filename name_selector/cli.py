"""Command-line entry point: ``name-selector {fetch,rank,explain,handles}``."""

import argparse
import logging
import sys
from pathlib import Path

from name_selector import dataset, ine
from name_selector.handles import BadHandle, find_bad_handles, generate_handles
from name_selector.models import ScoredName, Sex
from name_selector.scoring import (
    DEFAULT_WEIGHTS,
    excluded_by_handles,
    explain,
    parse_weights,
    rank,
)

CRITERIA = list(DEFAULT_WEIGHTS)
RAW_DIR = dataset.DEFAULT_DATA_DIR.parent / "raw"


def _format_row(position: int, s: ScoredName) -> str:
    cells = " ".join(f"{s.criteria[k]:>9.2f}" for k in CRITERIA)
    shape = f"{s.syllables.count}·{s.syllables.stress.value}"
    return f"{position:>3}  {s.candidate.written:<11} {s.total:>5.3f} {cells}  {shape}"


def cmd_fetch(args: argparse.Namespace) -> int:
    years = tuple(args.years)
    ine.fetch(args.raw_dir, years)
    ine.build(args.raw_dir, args.data_dir, years)
    print(f"INE data refreshed into {args.data_dir}")
    return 0


def _describe(hit: BadHandle) -> str:
    return f"{hit.handle} ({hit.pattern}) -> '{hit.word}' [{hit.tier.value}]"


def cmd_rank(args: argparse.Namespace) -> int:
    candidates, census = dataset.load(args.data_dir, args.sex)
    weights = parse_weights(args.weights)
    ranked = rank(candidates, census, weights, args.ascii_only, args.surnames)
    print(f"{'#':>3}  {'name':<11} {'total':>5} " + " ".join(f"{k:>9}" for k in CRITERIA))
    for i, s in enumerate(ranked[: args.top], start=1):
        print(_format_row(i, s))

    excluded = excluded_by_handles(candidates, args.surnames) if args.surnames else []
    if excluded:
        print(f"\nExcluded with surnames {' '.join(args.surnames)} (bad email/username):")
        for c, hits in excluded:
            print(f"  {c.written:<11} " + "; ".join(_describe(h) for h in hits))
    return 0


def cmd_handles(args: argparse.Namespace) -> int:
    """Show every generated handle for one full name and flag the bad ones."""
    hits = {h.handle: h for h in find_bad_handles(args.name, args.surnames)}
    for handle in generate_handles(args.name, args.surnames):
        hit = hits.get(handle.text)
        verdict = f"BAD  '{hit.word}' [{hit.tier.value}]" if hit else "ok"
        print(f"  {handle.text:<24} {handle.pattern:<18} {verdict}")
    return 1 if hits else 0


def cmd_explain(args: argparse.Namespace) -> int:
    candidates, census = dataset.load(args.data_dir, args.sex)
    ages = dataset.load_ages(args.data_dir, args.sex)
    result = explain(args.name, candidates, census, parse_weights(args.weights), ages)
    s, c = result.scored, result.scored.candidate
    people = "women" if args.sex is Sex.FEMALE else "men"
    if result.position:
        place = f"#{result.position} of {result.pool_size}"
    else:
        place = f"not in the INE newborn top-100 ({result.pool_size} names)"
    births = ", ".join(f"{y}: {n}" for y, n in sorted(c.births.items())) or "outside the top 100"
    print(f"{c.written}  —  {place}, total {s.total:.3f}")
    people_line = f"{people} in Spain with this name"
    print(f"  {people_line:<29} : {c.census_frequency:,} (mean age {c.census_mean_age})")
    print(f"  newborns                      : {births}")
    print(f"  syllables / stress            : {s.syllables.count} / {s.syllables.stress.value}")
    for k in CRITERIA:
        print(f"  {k:<29} : {s.criteria[k]:.2f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="name-selector", description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=dataset.DEFAULT_DATA_DIR)
    parser.add_argument(
        "--sex",
        type=Sex,
        choices=list(Sex),
        default=Sex.FEMALE,
        metavar="{female,male}",
        help="girls' or boys' names (default: female)",
    )
    parser.add_argument(
        "--weights",
        help=f"override weights, e.g. 'song=0.4,ascii=0'. Criteria: {', '.join(CRITERIA)}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="download INE spreadsheets and rebuild the CSVs")
    fetch.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    fetch.add_argument("--years", type=int, nargs="+", default=list(ine.DEFAULT_BIRTH_YEARS))
    fetch.set_defaults(func=cmd_fetch)

    rank_cmd = sub.add_parser("rank", help="rank names")
    rank_cmd.add_argument("--top", type=int, default=20)
    rank_cmd.add_argument("--ascii-only", action="store_true", help="drop names with accents")
    rank_cmd.add_argument(
        "--surnames",
        nargs="+",
        metavar="SURNAME",
        help="drop names whose future email/username with these surnames spells a bad word",
    )
    rank_cmd.set_defaults(func=cmd_rank)

    explain_cmd = sub.add_parser("explain", help="show the score breakdown for any name")
    explain_cmd.add_argument("name")
    explain_cmd.set_defaults(func=cmd_explain)

    handles = sub.add_parser("handles", help="check email/username combos for one full name")
    handles.add_argument("name")
    handles.add_argument("surnames", nargs="+", metavar="SURNAME")
    handles.set_defaults(func=cmd_handles)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"missing data file {exc.filename}; run `name-selector fetch` first", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
