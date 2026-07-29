import gc

import pytest


@pytest.fixture(autouse=True)
def collect_component_resources():
    yield
    gc.collect()
