"""Command-line greeting app."""

from __future__ import annotations

import argparse


def greet(name: str) -> str:
    """Return a friendly greeting for the provided name."""
    cleaned_name = name.strip()
    if not cleaned_name:
        cleaned_name = "World"
    return f"Hello, {cleaned_name}!"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print a friendly greeting.")
    parser.add_argument("--name", default="World", help="Name to greet")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(greet(args.name))


if __name__ == "__main__":
    main()
