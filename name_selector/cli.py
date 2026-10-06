"""Command-line entry point: ``name-selector {fetch,rank,explain}``."""

import argparse
import logging
import sys
from pathlib import Path

from name_selector import dataset, ine
from name_selector.models import ScoredName
from name_selector.phonetics import strip_accents
from name_selector.scoring import DEFAULT_WEIGHTS, parse_weights, rank

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


def cmd_rank(args: argparse.Namespace) -> int:
    candidates, census = dataset.load(args.data_dir)
    ranked = rank(candidates, census, parse_weights(args.weights), ascii_only=args.ascii_only)
    print(f"{'#':>3}  {'name':<11} {'total':>5} " + " ".join(f"{k:>9}" for k in CRITERIA))
    for i, s in enumerate(ranked[: args.top], start=1):
        print(_format_row(i, s))
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    candidates, census = dataset.load(args.data_dir)
    ranked = rank(candidates, census, parse_weights(args.weights))
    wanted = strip_accents(args.name).upper()
    for position, s in enumerate(ranked, start=1):
        if s.candidate.key != wanted:
            continue
        c = s.candidate
        births = ", ".join(f"{y}: {n}" for y, n in sorted(c.births.items()))
        print(f"{c.written}  —  #{position} of {len(ranked)}, total {s.total:.3f}")
        age = c.census_mean_age
        print(f"  women in Spain with this name : {c.census_frequency:,} (mean age {age})")
        print(f"  newborn girls                 : {births}")
        print(f"  syllables / stress            : {s.syllables.count} / {s.syllables.stress.value}")
        for k in CRITERIA:
            print(f"  {k:<29} : {s.criteria[k]:.2f}")
        return 0
    print(f"{args.name!r} is not in the INE newborn top-100 pool", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="name-selector", description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=dataset.DEFAULT_DATA_DIR)
    parser.add_argument(
        "--weights",
        help=f"override weights, e.g. 'song=0.4,ascii=0'. Criteria: {', '.join(CRITERIA)}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="download INE spreadsheets and rebuild the CSVs")
    fetch.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    fetch.add_argument("--years", type=int, nargs="+", default=list(ine.DEFAULT_BIRTH_YEARS))
    fetch.set_defaults(func=cmd_fetch)

    rank_cmd = sub.add_parser("rank", help="rank girls' names")
    rank_cmd.add_argument("--top", type=int, default=20)
    rank_cmd.add_argument("--ascii-only", action="store_true", help="drop names with accents")
    rank_cmd.set_defaults(func=cmd_rank)

    explain = sub.add_parser("explain", help="show the score breakdown for one name")
    explain.add_argument("name")
    explain.set_defaults(func=cmd_explain)
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
