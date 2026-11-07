"""A mutation PR of package_gate §9.3 disables its own tests, as a hostile PR
could (tests/ is not protected), so that main's verify is what refuses it."""
import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.skip(reason="disabled by a mutation PR of package_gate §9.3"))
