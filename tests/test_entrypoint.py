import unittest

import app_qt


class EntrypointTests(unittest.TestCase):
    def test_app_qt_exports_main_for_app_entrypoint(self):
        self.assertTrue(callable(app_qt.main))


if __name__ == "__main__":
    unittest.main()
