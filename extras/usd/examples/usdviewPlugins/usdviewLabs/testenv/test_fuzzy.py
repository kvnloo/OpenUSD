import unittest

from usdviewLabs.fuzzy import ranked, score


class FuzzyTest(unittest.TestCase):
    def test_prefix_beats_substring(self):
        self.assertGreater(score("world", "World/Car"),
                           score("world", "Open /World/Car"))

    def test_subsequence(self):
        self.assertIsNotNone(score("wcr", "/World/Car"))

    def test_nonmatch(self):
        self.assertIsNone(score("xyz", "/World/Car"))

    def test_ranked_limit(self):
        values = ranked("a", ["a", "ab", "ba", "zz"], limit=2)
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0], "a")


if __name__ == "__main__":
    unittest.main()
