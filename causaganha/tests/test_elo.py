import unittest
import math # For math.isclose

# Add causaganha to sys.path to allow direct import of legalelo
# This is often needed when running tests from the tests directory or via discovery
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent)) # Adds repo root to path

from causaganha.legalelo import elo # elo.py is in legalelo folder

class TestEloCalculations(unittest.TestCase):

    def test_expected_score_equal_ratings(self):
        self.assertAlmostEqual(elo.expected_score(1500, 1500), 0.5)

    def test_expected_score_higher_rating(self):
        # Significantly higher rating for A, e.g., 400 points difference
        # E_A = 1 / (1 + 10^((1500 - 1900) / 400)) = 1 / (1 + 10^(-1)) = 1 / 1.1 = 0.9090...
        self.assertAlmostEqual(elo.expected_score(1900, 1500), 1 / (1 + math.pow(10, -1)), places=4)
        self.assertTrue(elo.expected_score(1900, 1500) > 0.9) # A is much more likely to win

    def test_expected_score_lower_rating(self):
        # Significantly lower rating for A
        # E_A = 1 / (1 + 10^((1900 - 1500) / 400)) = 1 / (1 + 10^(1)) = 1 / 11 = 0.0909...
        self.assertAlmostEqual(elo.expected_score(1500, 1900), 1 / (1 + math.pow(10, 1)), places=4)
        self.assertTrue(elo.expected_score(1500, 1900) < 0.1) # A is much less likely to win

    def test_update_elo_equal_ratings_a_wins(self):
        r_a, r_b = 1500.0, 1500.0
        k = 16
        # Expected change = K * (S_A - E_A) = 16 * (1.0 - 0.5) = 8
        new_r_a, new_r_b = elo.update_elo(r_a, r_b, 1.0, k_factor=k)
        self.assertAlmostEqual(new_r_a, r_a + k * 0.5)
        self.assertAlmostEqual(new_r_b, r_b - k * 0.5)
        self.assertAlmostEqual(new_r_a + new_r_b, r_a + r_b) # Sum of Elo should be constant

    def test_update_elo_equal_ratings_a_loses(self):
        r_a, r_b = 1500.0, 1500.0
        k = 16
        # Expected change for A = K * (S_A - E_A) = 16 * (0.0 - 0.5) = -8
        new_r_a, new_r_b = elo.update_elo(r_a, r_b, 0.0, k_factor=k)
        self.assertAlmostEqual(new_r_a, r_a - k * 0.5)
        self.assertAlmostEqual(new_r_b, r_b + k * 0.5)
        self.assertAlmostEqual(new_r_a + new_r_b, r_a + r_b)

    def test_update_elo_equal_ratings_draw(self):
        r_a, r_b = 1500.0, 1500.0
        k = 16
        # Expected change for A = K * (S_A - E_A) = 16 * (0.5 - 0.5) = 0
        new_r_a, new_r_b = elo.update_elo(r_a, r_b, 0.5, k_factor=k)
        self.assertAlmostEqual(new_r_a, r_a)
        self.assertAlmostEqual(new_r_b, r_b)
        self.assertAlmostEqual(new_r_a + new_r_b, r_a + r_b)

    def test_update_elo_different_ratings_higher_wins(self):
        r_a, r_b = 1600.0, 1400.0
        k = 16
        e_a = elo.expected_score(r_a, r_b) # Expected > 0.5
        self.assertTrue(e_a > 0.5)
        change = k * (1.0 - e_a) # Should be positive, but smaller than k*0.5
        self.assertTrue(0 < change < k * 0.5)
        new_r_a, new_r_b = elo.update_elo(r_a, r_b, 1.0, k_factor=k)
        self.assertAlmostEqual(new_r_a, round(r_a + change, 2))
        self.assertAlmostEqual(new_r_b, round(r_b - change, 2))
        self.assertAlmostEqual(new_r_a + new_r_b, r_a + r_b) # Sum of Elo should still be very close to constant

    def test_update_elo_different_ratings_lower_wins_upset(self):
        r_a, r_b = 1400.0, 1600.0 # A is lower rated
        k = 16
        e_a = elo.expected_score(r_a, r_b) # Expected < 0.5
        self.assertTrue(e_a < 0.5)
        # Player A wins, score_a = 1.0
        change = k * (1.0 - e_a) # Should be positive and larger than k*0.5 (big gain for upset)
        self.assertTrue(change > k * 0.5)
        new_r_a, new_r_b = elo.update_elo(r_a, r_b, 1.0, k_factor=k)
        self.assertAlmostEqual(new_r_a, round(r_a + change, 2))
        self.assertAlmostEqual(new_r_b, round(r_b - change, 2))
        self.assertAlmostEqual(new_r_a + new_r_b, r_a + r_b) # Sum of Elo should still be very close to constant

    def test_update_elo_custom_k_factor(self):
        r_a, r_b = 1500.0, 1500.0
        k_custom = 32
        # Expected change = K_custom * (S_A - E_A) = 32 * (1.0 - 0.5) = 16
        new_r_a, new_r_b = elo.update_elo(r_a, r_b, 1.0, k_factor=k_custom)
        self.assertAlmostEqual(new_r_a, r_a + k_custom * 0.5)
        self.assertAlmostEqual(new_r_b, r_b - k_custom * 0.5)

    def test_update_elo_invalid_score(self):
        with self.assertRaises(ValueError):
            elo.update_elo(1500, 1500, 1.5) # score_a > 1
        with self.assertRaises(ValueError):
            elo.update_elo(1500, 1500, -0.5) # score_a < 0

    def test_elo_sum_conservation(self):
        # Test that the sum of elo ratings is conserved across different scenarios
        r_a_initial, r_b_initial = 1530.0, 1470.0
        k=elo.DEFAULT_K_FACTOR

        # Scenario 1: A wins
        new_r_a1, new_r_b1 = elo.update_elo(r_a_initial, r_b_initial, 1.0, k_factor=k)
        self.assertTrue(math.isclose(new_r_a1 + new_r_b1, r_a_initial + r_b_initial))

        # Scenario 2: B wins (A loses)
        new_r_a2, new_r_b2 = elo.update_elo(r_a_initial, r_b_initial, 0.0, k_factor=k)
        self.assertTrue(math.isclose(new_r_a2 + new_r_b2, r_a_initial + r_b_initial))

        # Scenario 3: Draw
        new_r_a3, new_r_b3 = elo.update_elo(r_a_initial, r_b_initial, 0.5, k_factor=k)
        self.assertTrue(math.isclose(new_r_a3 + new_r_b3, r_a_initial + r_b_initial))


if __name__ == '__main__':
    unittest.main()
