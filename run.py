"""Single entry point for Market Scanner Pro.

Run ``python run.py`` for a guided menu, or use one of the documented modes:
``live``, ``viewer``, ``scan``, ``train``, or ``all``.
"""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

MODES = {
    "live": "Run a live interactive scan in Streamlit",
    "viewer": "Open a completed local or Colab scan database",
    "scan": "Run the headless overnight scan and create scans_data.db",
    "train": "Train the neural network and create models/nn_weights.pt",
    "all": "Train the neural network, run the scan, then open the viewer",
}


def command_for(mode: str, port: int = 8501) -> list[list[str]]:
    """Return subprocess commands for a launcher mode (testable, no side effects)."""
    python = sys.executable
    streamlit = [python, "-m", "streamlit", "run"]
    commands = {
        "live": [streamlit + ["app.py", "--server.port", str(port)]],
        "viewer": [streamlit + ["app_v2.py", "--server.port", str(port)]],
        "scan": [[python, "run_nightly_scan.py"]],
        "train": [[python, "ml/train_model.py"]],
        "all": [
            [python, "ml/train_model.py"],
            [python, "run_nightly_scan.py"],
            streamlit + ["app_v2.py", "--server.port", str(port)],
        ],
    }
    if mode not in commands:
        raise ValueError(f"Unknown mode: {mode}")
    return commands[mode]


def choose_mode() -> str:
    print("\nMarket Scanner Pro\n")
    choices = list(MODES)
    for number, mode in enumerate(choices, start=1):
        print(f"  {number}. {MODES[mode]}")
    print()
    while True:
        selection = input("Choose 1-5 [2]: ").strip() or "2"
        if selection.isdigit() and 1 <= int(selection) <= len(choices):
            return choices[int(selection) - 1]
        print("Please enter a number from 1 to 5.")


def configure_llm(enable: bool, model: str | None = None, disable: bool = False) -> bool:
    """Configure optional LLM review for child processes without persisting secrets."""
    if disable:
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_REVIEW_MODEL", None)
        return False
    if model:
        os.environ["OPENAI_REVIEW_MODEL"] = model
    if os.getenv("OPENAI_API_KEY"):
        return True
    if not enable:
        return False
    key = getpass.getpass("OpenAI API key (hidden; not saved): ").strip()
    if not key:
        print("No key entered; continuing without LLM review.")
        return False
    os.environ["OPENAI_API_KEY"] = key
    return True


def run_mode(mode: str, port: int = 8501) -> int:
    print(f"\nStarting: {MODES[mode]}\n")
    for command in command_for(mode, port):
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode != 0:
            print(f"Step failed with exit code {result.returncode}.", file=sys.stderr)
            return result.returncode
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified Market Scanner Pro launcher")
    parser.add_argument("mode", nargs="?", choices=MODES, help="Operation to run; omit for the menu")
    parser.add_argument("--port", type=int, default=8501, help="Streamlit port (default: 8501)")
    llm_group = parser.add_mutually_exclusive_group()
    llm_group.add_argument("--llm", action="store_true", help="Enable LLM review; securely prompt if OPENAI_API_KEY is unset")
    llm_group.add_argument("--no-llm", action="store_true", help="Remove inherited API credentials and disable LLM review")
    parser.add_argument("--model", help="OpenAI review model (or set OPENAI_REVIEW_MODEL)")
    args = parser.parse_args(argv)
    menu_mode = args.mode is None
    mode = args.mode or choose_mode()
    enable_llm = args.llm
    if menu_mode and not args.no_llm and mode in {"live", "viewer", "all"} and not os.getenv("OPENAI_API_KEY"):
        answer = input("Enable optional multi-agent LLM review? [y/N]: ").strip().lower()
        enable_llm = answer in {"y", "yes"}
    llm_ready = configure_llm(enable_llm, args.model, disable=args.no_llm)
    print(f"LLM review: {'enabled' if llm_ready else 'disabled'}")
    try:
        return run_mode(mode, args.port)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
