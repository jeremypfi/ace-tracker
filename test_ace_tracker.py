#!/usr/bin/env python3
"""
Unit Tests for ACE Tracker
===========================
Tests for hurricane ACE calculation, storm categorization, and data validation.

Usage:
    python3 -m pytest test_ace_tracker.py -v
    or
    python3 test_ace_tracker.py
"""

import unittest
from datetime import datetime
from ace_tracker import (
    get_category,
    is_major,
    get_noaa_classification,
    finalize_storm,
    calculate_yearly_totals,
    find_similar_seasons,
    SYNOPTIC_TIMES,
    ACE_STATUSES,
    MIN_NAMED_STORM_WIND
)


class TestStormCategories(unittest.TestCase):
    """Test storm category classification"""

    def test_category_5_hurricane(self):
        """Test Cat 5 classification (>=137 kt)"""
        self.assertEqual(get_category(137), "Cat 5")
        self.assertEqual(get_category(150), "Cat 5")
        self.assertEqual(get_category(185), "Cat 5")

    def test_category_4_hurricane(self):
        """Test Cat 4 classification (113-136 kt)"""
        self.assertEqual(get_category(113), "Cat 4")
        self.assertEqual(get_category(125), "Cat 4")
        self.assertEqual(get_category(136), "Cat 4")

    def test_category_3_hurricane(self):
        """Test Cat 3 classification (96-112 kt)"""
        self.assertEqual(get_category(96), "Cat 3")
        self.assertEqual(get_category(105), "Cat 3")
        self.assertEqual(get_category(112), "Cat 3")

    def test_category_2_hurricane(self):
        """Test Cat 2 classification (83-95 kt)"""
        self.assertEqual(get_category(83), "Cat 2")
        self.assertEqual(get_category(90), "Cat 2")
        self.assertEqual(get_category(95), "Cat 2")

    def test_category_1_hurricane(self):
        """Test Cat 1 classification (64-82 kt)"""
        self.assertEqual(get_category(64), "Cat 1")
        self.assertEqual(get_category(75), "Cat 1")
        self.assertEqual(get_category(82), "Cat 1")

    def test_tropical_storm(self):
        """Test TS classification (34-63 kt)"""
        self.assertEqual(get_category(34), "TS")
        self.assertEqual(get_category(50), "TS")
        self.assertEqual(get_category(63), "TS")

    def test_tropical_depression(self):
        """Test TD classification (<34 kt)"""
        self.assertEqual(get_category(0), "TD")
        self.assertEqual(get_category(20), "TD")
        self.assertEqual(get_category(33), "TD")


class TestMajorHurricanes(unittest.TestCase):
    """Test major hurricane identification (Cat 3+)"""

    def test_major_hurricane_threshold(self):
        """Test that 96 kt is the major hurricane threshold"""
        self.assertTrue(is_major(96))
        self.assertTrue(is_major(150))
        self.assertFalse(is_major(95))
        self.assertFalse(is_major(64))

    def test_major_hurricane_all_categories(self):
        """Test major hurricane across all categories"""
        # Cat 5, 4, 3 are major
        self.assertTrue(is_major(137))  # Cat 5
        self.assertTrue(is_major(113))  # Cat 4
        self.assertTrue(is_major(96))   # Cat 3

        # Cat 2, 1, TS, TD are not major
        self.assertFalse(is_major(83))  # Cat 2
        self.assertFalse(is_major(64))  # Cat 1
        self.assertFalse(is_major(34))  # TS
        self.assertFalse(is_major(20))  # TD


class TestACECalculation(unittest.TestCase):
    """Test ACE (Accumulated Cyclone Energy) calculation"""

    def test_ace_formula(self):
        """Test ACE calculation: sum(wind^2) / 10000"""
        storm = {
            'id': 'AL012025',
            'name': 'Test',
            'year': 2025,
            'max_wind': 100,
            'wind_readings': [64, 75, 85, 100, 95, 85, 70],
            'start_date': datetime(2025, 6, 1),
            'end_date': datetime(2025, 6, 8)
        }

        finalized = finalize_storm(storm)

        # Manual calculation: 64^2 + 75^2 + 85^2 + 100^2 + 95^2 + 85^2 + 70^2 = 48096
        # 48096 / 10000 = 4.8096
        expected_ace = sum(w**2 for w in storm['wind_readings']) / 10000
        expected_ace = round(expected_ace, 4)

        self.assertEqual(finalized['ace'], expected_ace)
        self.assertAlmostEqual(finalized['ace'], 4.8096, places=4)

    def test_ace_single_reading(self):
        """Test ACE with single wind reading"""
        storm = {
            'id': 'AL012025',
            'name': 'Weak',
            'year': 2025,
            'max_wind': 50,
            'wind_readings': [50],
            'start_date': datetime(2025, 6, 1),
            'end_date': datetime(2025, 6, 1)
        }

        finalized = finalize_storm(storm)
        expected_ace = (50 ** 2) / 10000

        self.assertEqual(finalized['ace'], round(expected_ace, 4))
        self.assertEqual(finalized['ace'], 0.25)

    def test_ace_no_readings(self):
        """Test ACE with no wind readings (should be 0)"""
        storm = {
            'id': 'AL012025',
            'name': 'Empty',
            'year': 2025,
            'max_wind': 0,
            'wind_readings': [],
            'start_date': None,
            'end_date': None
        }

        finalized = finalize_storm(storm)
        self.assertEqual(finalized['ace'], 0.0)

    def test_storm_duration_calculation(self):
        """Test storm duration in days"""
        storm = {
            'id': 'AL012025',
            'name': 'Long',
            'year': 2025,
            'max_wind': 70,
            'wind_readings': [70],
            'start_date': datetime(2025, 6, 1),
            'end_date': datetime(2025, 6, 10)
        }

        finalized = finalize_storm(storm)
        self.assertEqual(finalized['duration_days'], 10)


class TestNOAAClassification(unittest.TestCase):
    """Test NOAA season classification"""

    def test_atlantic_classifications(self):
        """Test Atlantic basin classifications"""
        # Thresholds: below_normal=73, near_normal_upper=126, above_normal_upper=159
        self.assertEqual(get_noaa_classification(50, 'atlantic'), "Below Normal")
        self.assertEqual(get_noaa_classification(73, 'atlantic'), "Near Normal")
        self.assertEqual(get_noaa_classification(100, 'atlantic'), "Near Normal")
        self.assertEqual(get_noaa_classification(125, 'atlantic'), "Near Normal")
        self.assertEqual(get_noaa_classification(126, 'atlantic'), "Above Normal")  # >= 126
        self.assertEqual(get_noaa_classification(130, 'atlantic'), "Above Normal")
        self.assertEqual(get_noaa_classification(158, 'atlantic'), "Above Normal")
        self.assertEqual(get_noaa_classification(159, 'atlantic'), "Extremely Active")  # >= 159
        self.assertEqual(get_noaa_classification(200, 'atlantic'), "Extremely Active")

    def test_pacific_classifications(self):
        """Test Eastern Pacific basin classifications"""
        # Thresholds: below_normal=73, near_normal_upper=126, above_normal_upper=159
        self.assertEqual(get_noaa_classification(50, 'pacific'), "Below Normal")
        self.assertEqual(get_noaa_classification(73, 'pacific'), "Near Normal")
        self.assertEqual(get_noaa_classification(125, 'pacific'), "Near Normal")
        self.assertEqual(get_noaa_classification(126, 'pacific'), "Above Normal")  # >= 126
        self.assertEqual(get_noaa_classification(158, 'pacific'), "Above Normal")
        self.assertEqual(get_noaa_classification(159, 'pacific'), "Extremely Active")  # >= 159
        self.assertEqual(get_noaa_classification(200, 'pacific'), "Extremely Active")


class TestYearlyTotals(unittest.TestCase):
    """Test yearly ACE totals calculation"""

    def test_calculate_yearly_totals(self):
        """Test summing ACE by year"""
        storms = [
            {'name': 'A', 'year': 2025, 'ace': 10.5},
            {'name': 'B', 'year': 2025, 'ace': 20.3},
            {'name': 'C', 'year': 2024, 'ace': 15.2},
            {'name': 'D', 'year': 2024, 'ace': 25.8},
            {'name': 'E', 'year': 2023, 'ace': 30.1},
        ]

        totals = calculate_yearly_totals(storms)

        self.assertEqual(totals[2025], 30.8)
        self.assertEqual(totals[2024], 41.0)
        self.assertEqual(totals[2023], 30.1)

    def test_empty_storm_list(self):
        """Test with no storms"""
        totals = calculate_yearly_totals([])
        self.assertEqual(totals, {})


class TestSimilarSeasons(unittest.TestCase):
    """Test finding similar historical seasons"""

    def test_find_similar_seasons(self):
        """Test finding 3 most similar seasons by ACE"""
        yearly_totals = {
            2020: 180.0,
            2019: 133.0,
            2018: 136.4,
            2017: 225.0,
            2016: 155.0,
            2015: 65.0,
        }

        # Find seasons similar to ACE=135
        similar = find_similar_seasons(135.0, yearly_totals)

        self.assertEqual(len(similar), 3)
        # Should find 2018 (136.4), 2019 (133.0), 2016 (155.0)
        self.assertEqual(similar[0][0], 2018)  # Closest
        self.assertEqual(similar[1][0], 2019)  # Second closest
        self.assertEqual(similar[2][0], 2016)  # Third closest

    def test_exclude_current_year(self):
        """Test that current year is excluded from similar seasons"""
        yearly_totals = {
            2025: 135.0,
            2024: 136.0,
            2023: 134.0,
        }

        similar = find_similar_seasons(135.0, yearly_totals, exclude_year=2025)

        # Should not include 2025
        years = [year for year, _ in similar]
        self.assertNotIn(2025, years)


class TestConstants(unittest.TestCase):
    """Test configuration constants"""

    def test_synoptic_times(self):
        """Test synoptic time values"""
        self.assertEqual(SYNOPTIC_TIMES, ['0000', '0600', '1200', '1800'])
        self.assertEqual(len(SYNOPTIC_TIMES), 4)

    def test_ace_statuses(self):
        """Test ACE-counting storm statuses"""
        self.assertEqual(ACE_STATUSES, ['TS', 'HU', 'SS'])
        self.assertIn('TS', ACE_STATUSES)  # Tropical Storm
        self.assertIn('HU', ACE_STATUSES)  # Hurricane
        self.assertIn('SS', ACE_STATUSES)  # Subtropical Storm

    def test_min_named_storm_wind(self):
        """Test minimum wind speed for named storm"""
        self.assertEqual(MIN_NAMED_STORM_WIND, 34)


class TestDataValidation(unittest.TestCase):
    """Test data validation and edge cases"""

    def test_negative_wind_speed(self):
        """Test handling of negative wind speeds"""
        # Category function should handle edge cases
        # (In production, add validation to reject negative values)
        result = get_category(-10)
        self.assertEqual(result, "TD")  # Current behavior

    def test_extreme_wind_speed(self):
        """Test handling of extreme wind speeds"""
        # Test very high wind speeds
        result = get_category(250)
        self.assertEqual(result, "Cat 5")

    def test_zero_ace_division(self):
        """Test that division by zero is handled"""
        # This is tested in the actual code with: (x / y) if y > 0 else 0
        # No direct function to test, but documented for completeness
        pass


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
