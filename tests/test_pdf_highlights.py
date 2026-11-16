import unittest
from unittest.mock import MagicMock

from pdf_highlights import keyword_rects


class HighlightFallbackTests(unittest.TestCase):
    def test_word_geometry_when_native_search_misses(self):
        page = MagicMock()
        page.search_for.return_value = []
        page.get_text.return_value = [
            (10, 20, 50, 32, "CLIMATE", 0, 0, 0),
            (52, 20, 75, 32, "RISK", 0, 0, 1),
        ]
        rects = keyword_rects(page, ["climate risk"])
        self.assertEqual(len(rects), 1)
        self.assertEqual(tuple(rects[0]), (10.0, 20.0, 75.0, 32.0))


if __name__ == "__main__":
    unittest.main()
