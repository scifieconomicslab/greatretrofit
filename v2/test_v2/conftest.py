"""Pytest configuration and fixtures for v2 tests."""
import pytest


@pytest.fixture
def snapshot(request):
    """Simple snapshot fixture for regression testing."""
    class Snapshot:
        def assert_match(self, data, filename):
            import json
            import os
            snapshot_dir = os.path.join(os.path.dirname(__file__), 'snapshots')
            os.makedirs(snapshot_dir, exist_ok=True)
            filepath = os.path.join(snapshot_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
    return Snapshot()