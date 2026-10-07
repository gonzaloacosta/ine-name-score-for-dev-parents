"""The site must work at the domain root and under a path prefix (gonzaloacosta.me/name-score/)."""

import re
from pathlib import Path

import pytest

PUBLIC = Path(__file__).resolve().parent.parent / "public"
# A URL starting with a single "/" ignores the prefix and escapes to the host's root.
ROOT_ABSOLUTE = re.compile(
    r"""(?:src|href|action)=["']/(?!/)"""  # HTML attributes
    r"""|url\(\s*["']?/(?!/)"""  # CSS url()
    r"""|from\s+["']/(?!/)"""  # ES module imports
    r"""|fetch\(\s*[`"']/(?!/)"""  # fetch calls
    r"""|[`"']/(?:nombre\.html|\?)""",  # links built in JS
)


@pytest.mark.parametrize(
    "path",
    sorted(p.name for p in PUBLIC.glob("*.*") if p.suffix in {".html", ".js", ".css"}),
)
def test_public_files_use_only_relative_urls(path):
    text = (PUBLIC / path).read_text(encoding="utf-8")

    offenders = [m.group(0) for m in ROOT_ABSOLUTE.finditer(text)]

    assert offenders == [], (
        f"{path} has root-absolute URLs that break under a path prefix: {offenders}"
    )


def test_repo_links_use_the_new_name():
    for page in ("index.html", "nombre.html"):
        html = (PUBLIC / page).read_text(encoding="utf-8")
        assert "github.com/gonzaloacosta/name-score" in html
        assert "ine-name-score-for-dev-parents" not in html
