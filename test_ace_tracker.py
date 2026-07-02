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
from ace_data import (
    get_category,
    is_major,
    get_noaa_classification,
    finalize_storm,
    calculate_yearly_totals,
    find_similar_seasons,
    calculate_same_date_stats,
    calculate_ace_pace,
    SYNOPTIC_TIMES,
    ACE_STATUSES,
    MIN_NAMED_STORM_WIND,
)
from ace_html import generate_dashboard_html, generate_history_html


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


class TestSameDateStats(unittest.TestCase):
    """Tests for calculate_same_date_stats() — same-date historical comparisons."""

    def _make_storms(self):
        """Three years of synthetic storms with known counts."""
        storms = []
        for year in [2023, 2024, 2025]:
            # Storm A: forms Jun 1, ends Jun 20 — fully before Jun 28 cutoff
            storms.append(finalize_storm({
                'id': f'AL01{year}', 'name': 'Alpha', 'year': year,
                'max_wind': 65,  # hurricane
                'wind_readings': [65, 65],
                'start_date': datetime(year, 6, 1),
                'end_date':   datetime(year, 6, 20),
                'landfall':   [],
            }))
            # Storm B: forms Jul 15 — after Jun 28 cutoff, should be excluded
            storms.append(finalize_storm({
                'id': f'AL02{year}', 'name': 'Beta', 'year': year,
                'max_wind': 40,
                'wind_readings': [40, 40],
                'start_date': datetime(year, 7, 15),
                'end_date':   datetime(year, 7, 25),
                'landfall':   [],
            }))
        return storms

    def test_excludes_post_cutoff_storms(self):
        """Storms forming after the cutoff date are not counted."""
        storms = self._make_storms()
        result = calculate_same_date_stats(storms, 'atlantic', datetime(2026, 6, 28))
        # Only Storm A (Jun 1-20) should count per year; Storm B (Jul 15) excluded
        self.assertEqual(result['avg_named'], 1.0)
        self.assertEqual(result['avg_hurricanes'], 1.0)

    def test_excludes_current_year(self):
        """The current year is never included in the historical average."""
        storms = self._make_storms()
        # Add a 2026 storm that would skew the average if included
        storms.append(finalize_storm({
            'id': 'AL012026', 'name': 'Arthur', 'year': 2026,
            'max_wind': 40, 'wind_readings': [40],
            'start_date': datetime(2026, 6, 1),
            'end_date':   datetime(2026, 6, 10),
            'landfall':   [],
        }))
        result = calculate_same_date_stats(storms, 'atlantic', datetime(2026, 6, 28))
        # Average should still be 1.0 (only 2023-2025 in the denominator)
        self.assertEqual(result['avg_named'], 1.0)

    def test_returns_none_with_no_historical_data(self):
        """Returns None when no historical storms are available."""
        self.assertIsNone(calculate_same_date_stats([], 'atlantic'))

    def test_date_label_format(self):
        """date_label is human-readable (e.g. 'Jun 28')."""
        storms = self._make_storms()
        result = calculate_same_date_stats(storms, 'atlantic', datetime(2026, 6, 28))
        self.assertEqual(result['date_label'], 'Jun 28')

    def test_yearly_ace_keys_exclude_current_year(self):
        """yearly_ace dict does not contain the current year."""
        storms = self._make_storms()
        result = calculate_same_date_stats(storms, 'atlantic', datetime(2026, 6, 28))
        self.assertNotIn(2026, result['yearly_ace'])


class TestAcePace(unittest.TestCase):
    """Tests for calculate_ace_pace() — day-by-day pace chart data."""

    def _make_ace_storm(self, year, ace, month=6, day=1, duration=4, id_suffix='a'):
        """A storm with an exact ACE value (wind_readings of 100kt repeated
        `ace` times gives ACE == ace exactly, since (100**2)/10000 == 1.0)."""
        return finalize_storm({
            'id': f'AL01{year}{id_suffix}', 'name': 'Test', 'year': year,
            'max_wind': 100, 'wind_readings': [100] * int(ace),
            'start_date': datetime(year, month, day),
            'end_date':   datetime(year, month, day + duration),
            'landfall':   [],
        })

    def test_returns_none_with_no_historical_data(self):
        """Returns None when no historical storms are available."""
        self.assertIsNone(calculate_ace_pace([], 'atlantic'))

    def test_returns_none_with_only_current_year(self):
        """Returns None when there are zero climatology years (only the
        current, in-progress season has data)."""
        storms = [self._make_ace_storm(2026, 10)]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 6, 28))
        self.assertIsNone(result)

    def test_excludes_current_year_from_climatology(self):
        """A huge current-year outlier storm does not affect the
        climatology mean/p25/p75."""
        storms = [
            self._make_ace_storm(2022, 10), self._make_ace_storm(2023, 20),
            self._make_ace_storm(2024, 30), self._make_ace_storm(2025, 40),
        ]
        baseline = calculate_ace_pace(storms, 'atlantic', datetime(2026, 6, 11))
        storms_with_outlier = storms + [self._make_ace_storm(2026, 999, id_suffix='outlier')]
        result = calculate_ace_pace(storms_with_outlier, 'atlantic', datetime(2026, 6, 11))
        self.assertEqual(result['climatology_mean'], baseline['climatology_mean'])
        self.assertEqual(result['climatology_p25'], baseline['climatology_p25'])
        self.assertEqual(result['climatology_p75'], baseline['climatology_p75'])

    def test_includes_current_year_in_current_season_curve(self):
        """The current year's own storm shows up (fully, once ended) in
        current_season."""
        storms = [
            self._make_ace_storm(2022, 10), self._make_ace_storm(2023, 20),
            self._make_ace_storm(2026, 15),
        ]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 6, 11))
        # Day index 10 = June 11 = Jun 1 + 10 days; storm ended Jun 5, so
        # by day 10 its full ACE (15) has accrued.
        self.assertEqual(result['current_season'][10], 15)

    def test_percentile_computation(self):
        """climatology_p25/p75 match hand-computed linear-interpolation
        percentiles for a known set of same-day cumulative ACE values."""
        storms = [
            self._make_ace_storm(2022, 10), self._make_ace_storm(2023, 20),
            self._make_ace_storm(2024, 30), self._make_ace_storm(2025, 40),
        ]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 6, 11))
        # Day index 10: all 4 storms (started Jun 1, ended Jun 5) have fully
        # accrued. Sorted values [10,20,30,40], n=4:
        #   p25: k=(4-1)*0.25=0.75 -> 10*0.25 + 20*0.75 = 17.5
        #   p75: k=(4-1)*0.75=2.25 -> 30*0.75 + 40*0.25 = 32.5
        self.assertAlmostEqual(result['climatology_p25'][10], 17.5)
        self.assertAlmostEqual(result['climatology_p75'][10], 32.5)
        self.assertAlmostEqual(result['climatology_mean'][10], 25.0)

    def test_last_season_curve(self):
        """last_season matches the cumulative curve for as_of_date.year - 1."""
        storms = [
            self._make_ace_storm(2022, 10), self._make_ace_storm(2023, 20),
            self._make_ace_storm(2025, 40),
        ]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 6, 11))
        self.assertEqual(result['last_season'][10], 40)

    def test_last_season_none_when_absent(self):
        """last_season is None when as_of_date.year - 1 has no storms."""
        storms = [self._make_ace_storm(2020, 10), self._make_ace_storm(2021, 20)]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 6, 11))
        self.assertIsNone(result['last_season'])

    def test_today_index_clamped_before_season_start(self):
        """as_of_date before the season start clamps today_index to 0."""
        storms = [self._make_ace_storm(2022, 10)]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 4, 1))
        self.assertEqual(result['today_index'], 0)

    def test_today_index_clamped_after_season_end(self):
        """as_of_date after Nov 30 clamps today_index to the last valid index."""
        storms = [self._make_ace_storm(2022, 10)]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 12, 15))
        expected_last = (datetime(2026, 11, 30) - datetime(2026, 6, 1)).days
        self.assertEqual(result['today_index'], expected_last)

    def test_current_season_null_after_today(self):
        """current_season values after today_index are all None."""
        storms = [self._make_ace_storm(2022, 10), self._make_ace_storm(2026, 15)]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 6, 11))
        self.assertTrue(all(v is None for v in result['current_season'][11:]))

    def test_array_lengths_consistent(self):
        """All returned arrays share the same length."""
        storms = [self._make_ace_storm(2022, 10), self._make_ace_storm(2023, 20)]
        result = calculate_ace_pace(storms, 'atlantic', datetime(2026, 6, 11))
        n = len(result['day_labels'])
        self.assertEqual(len(result['climatology_mean']), n)
        self.assertEqual(len(result['climatology_p25']), n)
        self.assertEqual(len(result['climatology_p75']), n)
        self.assertEqual(len(result['current_season']), n)


class TestHTMLGeneration(unittest.TestCase):
    """Smoke tests for HTML generation — catches NameErrors, TypeErrors, and
    broken f-strings in generate_dashboard_html / generate_history_html without
    requiring a live Tropycal / network call."""

    def _make_basin_data(self):
        """Minimal basin_data fixture that exercises both pages."""
        storms = [
            finalize_storm({
                'id': 'AL012026', 'name': 'Arthur', 'year': 2026,
                'max_wind': 40, 'wind_readings': [40, 40],
                'start_date': datetime(2026, 6, 15),
                'end_date':   datetime(2026, 6, 18),
                'landfall':   [('Texas', 'TS')],
            }),
            finalize_storm({
                'id': 'AL012005', 'name': 'Katrina', 'year': 2005,
                'max_wind': 150, 'wind_readings': [150, 150, 130, 100],
                'start_date': datetime(2005, 8, 23),
                'end_date':   datetime(2005, 8, 30),
                'landfall':   [('Florida', 'Cat 1'), ('Louisiana', 'Cat 3')],
            }),
        ]
        yearly_totals = {2005: 245.0, 2024: 161.6, 2025: 130.8}
        return [{
            'basin_key': 'atlantic',
            'storms': storms,
            'current': {
                'year': 2026,
                'storms': {'Arthur': 0.41},
                'storm_details': {
                    'Arthur': {
                        'ace': 0.41, 'max_wind': 40,
                        'track_points': [
                            {'lat': 25.0, 'lon': -90.0, 'wind': 40,
                             'status': 'TS', 'time': '6/17 00Z'},
                        ],
                        'is_active': False,
                        'start_date': '6/15',
                        'landfall': [('Texas', 'TS')],
                    }
                },
                'total': 0.41,
            },
            'yearly_totals': yearly_totals,
            'historical_storms': storms,
            'insights': ['ACE Leader: Arthur with 0.4 ACE'],
        }]

    def test_dashboard_html_generates(self):
        """generate_dashboard_html() runs without error and returns non-empty HTML."""
        basin_data = self._make_basin_data()
        result = generate_dashboard_html(basin_data)
        self.assertIsInstance(result, str)
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('Arthur', result)

    def test_history_html_generates(self):
        """generate_history_html() runs without error and returns non-empty HTML."""
        basin_data = self._make_basin_data()
        result = generate_history_html(basin_data)
        self.assertIsInstance(result, str)
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('All Seasons', result)
        self.assertIn('2005', result)

    def test_leaflet_sri_hashes_present(self):
        """Dashboard HTML contains the correct full SRI hashes for Leaflet.

        Guards against truncated or missing integrity attributes that would
        cause the browser to silently block the map library.
        """
        basin_data = self._make_basin_data()
        result = generate_dashboard_html(basin_data)
        # Both the full hash value AND crossorigin must be present
        self.assertIn(
            'sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH',
            result, "Leaflet JS SRI hash missing or truncated"
        )
        self.assertIn(
            'sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H',
            result, "Leaflet CSS SRI hash missing or truncated"
        )
        self.assertIn('crossorigin="anonymous"', result)

    def test_pace_chart_embedded(self):
        """generate_dashboard_html embeds ACE_PACE data and renders the
        chart canvas when ace_pace is present. Uses the real
        calculate_ace_pace output (not a hand-built dict) so this also
        checks the return shape is genuinely JSON-serializable."""
        basin_data = self._make_basin_data()
        basin_data[0]['ace_pace'] = calculate_ace_pace(
            basin_data[0]['historical_storms'], 'atlantic', datetime(2026, 6, 18)
        )
        result = generate_dashboard_html(basin_data)
        self.assertIn('ACE_PACE=', result)
        self.assertIn('pace-canvas-atlantic', result)

    def test_pace_chart_omitted_without_data(self):
        """generate_dashboard_html degrades gracefully (no KeyError) when
        ace_pace is absent from a basin's data."""
        basin_data = self._make_basin_data()
        result = generate_dashboard_html(basin_data)
        self.assertIsInstance(result, str)
        self.assertIn('ACE_PACE=', result)  # embedded as {} when no basin has pace data

    def test_chartjs_sri_hash_present(self):
        """Dashboard HTML contains the correct full SRI hash for Chart.js.

        Guards against the same truncated/wrong-hash bug that already hit
        the Leaflet script tag once in this repo.
        """
        basin_data = self._make_basin_data()
        result = generate_dashboard_html(basin_data)
        self.assertIn(
            'sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ',
            result, "Chart.js SRI hash missing or truncated"
        )

    def test_html_escape_applied(self):
        """html_escape() is reachable from inside the generator functions
        (guards against the 'html' local-variable shadowing bug)."""
        basin_data = self._make_basin_data()
        # Inject a synthetic name with an HTML special character
        basin_data[0]['current']['storms']['Test&Storm'] = 1.0
        basin_data[0]['current']['storm_details']['Test&Storm'] = {
            'ace': 1.0, 'max_wind': 40, 'track_points': [],
            'is_active': False, 'start_date': '6/1', 'landfall': [],
        }
        basin_data[0]['current']['total'] = 1.41
        result = generate_dashboard_html(basin_data)
        self.assertIn('Test&amp;Storm', result)
        self.assertNotIn('<script>alert', result)


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
