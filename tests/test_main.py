from src.main import greet


def test_greet_uses_name() -> None:
    assert greet("Codex") == "Hello, Codex!"


def test_greet_defaults_blank_name_to_world() -> None:
    assert greet("   ") == "Hello, World!"
