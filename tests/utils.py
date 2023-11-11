from __future__ import annotations

import contextlib
import os

from niquests.utils import getproxies, getproxies_environment


@contextlib.contextmanager
def override_environ(**kwargs):
    save_env = dict(os.environ)
    for key, value in kwargs.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value
    getproxies.cache_clear()
    getproxies_environment.cache_clear()
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(save_env)
        getproxies.cache_clear()
        getproxies_environment.cache_clear()
