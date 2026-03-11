from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "repos"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
TOOLS_ROOT = REPO_ROOT / "tools"


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        args,
        cwd=str(cwd or REPO_ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def run_json_script(script_name: str, *args: str, cwd: Path | None = None) -> dict:
    result = run_command([sys.executable, str(SCRIPTS_ROOT / script_name), *args], cwd=cwd)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from script {script_name}: {e}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        raise


class BaseRegintelTest(unittest.TestCase):
    maxDiff = None
    
    @property
    def repo_root(self) -> Path:
        return REPO_ROOT

    @property
    def fixtures_root(self) -> Path:
        return FIXTURES_ROOT

    @property
    def scripts_root(self) -> Path:
        return SCRIPTS_ROOT

    @property
    def tools_root(self) -> Path:
        return TOOLS_ROOT

    def run_command(self, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return run_command(args, cwd)

    def run_json_script(self, script_name: str, *args: str, cwd: Path | None = None) -> dict:
        return run_json_script(script_name, *args, cwd=cwd)
