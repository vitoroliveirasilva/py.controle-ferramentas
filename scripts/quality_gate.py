from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def run_command(command: Sequence[str], *, env: dict[str, str] | None = None) -> None:
    printable = " ".join(command)
    print(f"\n==> {printable}", flush=True)
    completed = subprocess.run(command, cwd=ROOT_DIR, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def build_test_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("APP_ENV", "testing")
    env.setdefault("SECRET_KEY", "quality-gate-secret")
    env.setdefault("AUTH_DEV_LOGIN_ENABLED", "1")
    env.setdefault("NOTIFICATIONS_EMAIL_ENABLED", "0")
    env.setdefault("BRASIF_GATEWAY_API_KEY", "")
    env.setdefault("DATABASE_URL", "")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa validações locais de qualidade, testes e build Docker opcional."
    )
    parser.add_argument(
        "--include-docker",
        action="store_true",
        help="Também executa docker compose build após lint e testes.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Executa apenas compile/lint, útil em investigação rápida.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env = build_test_environment()

    run_command(
        [sys.executable, "-m", "compileall", "-q", "app", "tests", "scripts"], env=env
    )
    run_command([sys.executable, "-m", "ruff", "check", "."], env=env)

    if not args.skip_tests:
        run_command([sys.executable, "-m", "pytest", "-q"], env=env)

    if args.include_docker:
        run_command(["docker", "compose", "build"], env=env)

    print("\nQuality gate finalizado com sucesso.", flush=True)


if __name__ == "__main__":
    main()
