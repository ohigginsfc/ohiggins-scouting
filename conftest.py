"""Install isolation before importing application modules or collecting tests."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent / 'src'))
_isolation = pytest.MonkeyPatch()


def pytest_configure(config):
    from tests.safety import isolate_environment, install_guards
    try:
        isolate_environment(_isolation)
        install_guards(_isolation)
    except (RuntimeError, ValueError) as exc:
        raise pytest.UsageError(str(exc)) from None


def pytest_unconfigure(config):
    _isolation.undo()
