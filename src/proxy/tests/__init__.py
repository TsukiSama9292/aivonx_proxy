"""Tests for the proxy app.

Provide an explicit TestLoader `load_tests` so we can control module
load order. This ensures `test_views.py` is discovered and run before
`test_views_proxy.py`.
"""

__all__ = [
    # test modules are discovered automatically
]


def load_tests(loader, tests, pattern):
    """Custom load_tests to order test modules.

    Load `test_views` first, then `test_views_proxy`, then any remaining
    test modules discovered by the loader.
    """
    import pkgutil
    import importlib
    from unittest import TestSuite

    suite = TestSuite()

    # Explicit desired order
    ordered = [
        'proxy.tests.test_views',
        'proxy.tests.test_views_proxy',
    ]

    # Load ordered modules first (ignore failures to import non-existent)
    import logging
    for mod_name in ordered:
        try:
            mod = importlib.import_module(mod_name)
            suite.addTests(loader.loadTestsFromModule(mod))
        except Exception as e:
            logging.getLogger('proxy.tests').debug("load_tests: failed to import %s: %s", mod_name, e)

    # Discover remaining modules in package and load any not already loaded
    package = importlib.import_module('proxy.tests')
    for finder, name, ispkg in pkgutil.iter_modules(package.__path__):
        full = f'proxy.tests.{name}'
        if full in ordered:
            continue
        try:
            mod = importlib.import_module(full)
            suite.addTests(loader.loadTestsFromModule(mod))
        except Exception as e:
            logging.getLogger('proxy.tests').debug("load_tests: skipping module %s due to import error: %s", full, e)

    return suite
