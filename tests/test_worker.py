"""Runs the Cloudflare Worker's own tests (node:test) as part of the Python suite and CI."""

import shutil
import subprocess
from pathlib import Path

import pytest

WORKER_TESTS = (
    Path(__file__).resolve().parent.parent / "deploy" / "cloudflare-worker" / "worker.test.mjs"
)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_cloudflare_worker():
    result = subprocess.run(["node", "--test", str(WORKER_TESTS)], capture_output=True, text=True)

    assert result.returncode == 0, result.stdout + result.stderr
