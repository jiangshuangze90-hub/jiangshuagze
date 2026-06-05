#!/usr/bin/env python3
"""Install Codex config entries that make DeepSeek selectable and callable."""
from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "codex-deepseek" / "model-catalog.json"
TOP_LEVEL_CATALOG = f'model_catalog_json = "{CATALOG}"'
DEFAULT_MODEL = 'model_provider = "deepseek"\nmodel = "deepseek-chat"'
PROVIDER_BLOCK = '''
# Added by jiangshuagze Codex DeepSeek setup.
[model_providers.deepseek]
name = "DeepSeek via local Responses bridge"
base_url = "http://127.0.0.1:5098/v1"
wire_api = "responses"
env_key = "DEEPSEEK_API_KEY"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 4
stream_max_retries = 5
stream_idle_timeout_ms = 300000
'''.strip()


def _first_table_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            return index
    return len(lines)


def _insert_top_level(existing: str, snippets: list[str]) -> str:
    if not snippets:
        return existing
    lines = existing.splitlines()
    insert_at = _first_table_index(lines)
    prefix = lines[:insert_at]
    suffix = lines[insert_at:]
    insertion = []
    if prefix and prefix[-1].strip():
        insertion.append("")
    insertion.extend("\n".join(snippets).splitlines())
    if suffix and insertion and insertion[-1].strip():
        insertion.append("")
    return "\n".join(prefix + insertion + suffix).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Add DeepSeek provider/model catalog settings to Codex config.toml.")
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"), help="Codex home directory; defaults to ~/.codex")
    parser.add_argument("--set-default", action="store_true", help="Also set DeepSeek Chat as the default Codex model/provider")
    args = parser.parse_args()

    codex_home = Path(args.codex_home).expanduser()
    codex_home.mkdir(parents=True, exist_ok=True)
    config = codex_home / "config.toml"
    existing = config.read_text(encoding="utf-8") if config.exists() else ""

    top_level: list[str] = []
    if "model_catalog_json" not in existing:
        top_level.append(TOP_LEVEL_CATALOG)
    if args.set_default and 'model_provider = "deepseek"' not in existing:
        top_level.append(DEFAULT_MODEL)

    updated = _insert_top_level(existing, top_level)
    if "[model_providers.deepseek]" not in updated:
        updated = updated.rstrip() + "\n\n" + PROVIDER_BLOCK + "\n"

    if updated != existing:
        config.write_text(updated, encoding="utf-8")
        print(f"Updated {config}")
    else:
        print(f"No changes needed in {config}")

    print("Next steps:")
    print("  1. export DEEPSEEK_API_KEY=your_key")
    print("  2. python3 scripts/deepseek_codex_bridge.py")
    print("  3. Restart Codex, then select DeepSeek Chat/Reasoner from the model dropdown or run:")
    print("     codex -c model_provider=deepseek -c model=deepseek-chat")


if __name__ == "__main__":
    main()
