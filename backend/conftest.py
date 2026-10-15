# conftest.py
# pytest configuration for OmniScan backend tests.
# Sets the asyncio mode so pytest-asyncio works without per-test decorators
# needing extra config.

import pytest

# Tell pytest-asyncio to treat every async test function as asyncio-based.
# This avoids having to add @pytest.mark.asyncio to every single test.
pytest_plugins = ['pytest_asyncio']
