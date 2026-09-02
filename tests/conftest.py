"""Shared pytest fixtures for the CFS test suite."""

import pytest


@pytest.fixture(autouse=True)
def clipboard(monkeypatch):
    """Stop the test suite from writing to the real system clipboard.

    Several commands (`exec`, `handoff create`, `handoff pickup`) copy their
    output with ``pyperclip.copy``. Nothing mocked it, so a full ``pytest`` run
    pushed a dozen-odd entries onto the developer's actual clipboard — one per
    test that reached those paths, each with a throwaway pytest tmp_path in it.

    Autouse so no test can opt out by forgetting. The yielded list records what
    each test copied, so a test that cares can request this fixture by name and
    assert on the content rather than only on stdout.
    """
    copied: list[str] = []

    try:
        import pyperclip
    except ImportError:
        # pyperclip is an optional dependency; the code under test already
        # degrades gracefully when it is missing, so there is nothing to patch.
        yield copied
        return

    monkeypatch.setattr(pyperclip, "copy", copied.append)
    yield copied
