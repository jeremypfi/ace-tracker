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

import io
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import ace_data
import ace_cards
import ace_feeds
from ace_data import (
    get_category,
    is_major,
    get_noaa_classification,
    ace_from_winds,
    finalize_storm,
    calculate_yearly_totals,
    rank_current_season,
    find_similar_seasons,
    find_highest_ace_storm,
    find_longest_lived_storm,
    find_strongest_landfall,
    find_earliest_forming_storm,
    find_latest_forming_storm,
    find_storms_on_this_day,
    calculate_same_date_stats,
    calculate_ace_pace,
    calculate_yearly_stats,
    calculate_records_in_play,
    parse_tcr_index,
    match_tcr_reports,
    _first_tropical_storm_time,
    _first_track_time,
    _date_reached_ace,
    RECORD_WATCH_DAYS,
    fetch_tcr_reports,
    _clean_landfalls,
    landfall_ace_share,
    average_landfall_share,
    generate_insights,
    _drop_stale_storm_keys,
    _last_track_stamp,
    _drop_malformed_hurdat_rows,
    latest_track_time,
    _extract_spaghetti_tracks,
    SYNOPTIC_TIMES,
    ACE_STATUSES,
    MIN_NAMED_STORM_WIND,
)
from ace_html import (
    generate_dashboard_html, generate_history_html, generate_records_html, generate_about_html,
    _decade_label, _nhc_tcr_links_html, _records_in_play_html, _year_storm_list_html,
    _data_as_of_html, _intensity_bar_html,
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


class TestHighestAceStorm(unittest.TestCase):
    """Tests for find_highest_ace_storm() — the dynamic replacement for the
    hardcoded all-time-record constant that went stale (#117)."""

    def test_returns_highest_ace_storm(self):
        storms = [
            finalize_storm({
                'id': 'EP061978', 'name': 'Fico', 'year': 1978,
                'max_wind': 140, 'wind_readings': [140] * 10,
                'start_date': datetime(1978, 7, 9), 'end_date': datetime(1978, 7, 23),
                'landfall': [],
            }),
            finalize_storm({
                'id': 'CP012006', 'name': 'Ioke', 'year': 2006,
                'max_wind': 160, 'wind_readings': [160] * 14,
                'start_date': datetime(2006, 8, 20), 'end_date': datetime(2006, 9, 6),
                'landfall': [],
            }),
        ]
        result = find_highest_ace_storm(storms)
        self.assertEqual(result['name'], 'Ioke')

    def test_returns_none_for_empty_input(self):
        self.assertIsNone(find_highest_ace_storm([]))
        self.assertIsNone(find_highest_ace_storm(None))


class TestBasinRecords(unittest.TestCase):
    """Tests for the records-page helpers (#63): longest-lived storm,
    strongest landfall, and earliest/latest-forming storm."""

    def _make_storms(self):
        return [
            finalize_storm({
                'id': 'AL012003', 'name': 'Ana', 'year': 2003,
                'max_wind': 40, 'wind_readings': [40, 40],
                'start_date': datetime(2003, 4, 20), 'end_date': datetime(2003, 4, 24),
                'formation_date': datetime(2003, 4, 20),
                'landfall': [],
            }),
            finalize_storm({
                'id': 'AL122005', 'name': 'Katrina', 'year': 2005,
                'max_wind': 150, 'wind_readings': [150, 150],
                'start_date': datetime(2005, 8, 23), 'end_date': datetime(2005, 8, 30),
                'formation_date': datetime(2005, 8, 23),
                'landfall': [('Louisiana', 'Cat 3'), ('Florida', 'Cat 1')],
            }),
            finalize_storm({
                'id': 'EP092018', 'name': 'Willa', 'year': 2018,
                'max_wind': 140, 'wind_readings': [140, 140],
                'start_date': datetime(2018, 10, 20), 'end_date': datetime(2018, 10, 24),
                'formation_date': datetime(2018, 10, 20),
                'landfall': [('Sinaloa', 'Cat 5')],
            }),
            finalize_storm({
                'id': 'AL222005', 'name': 'Zeta', 'year': 2005,
                'max_wind': 55, 'wind_readings': [55] * 20,
                'start_date': datetime(2005, 12, 30), 'end_date': datetime(2006, 1, 20),
                'formation_date': datetime(2005, 12, 30),
                'landfall': [],
            }),
        ]

    def test_longest_lived_storm(self):
        result = find_longest_lived_storm(self._make_storms())
        self.assertEqual(result['name'], 'Zeta')

    def test_longest_lived_ignores_zero_duration(self):
        storms = [{'name': 'NoDuration', 'duration_days': 0, 'ace': 5}]
        self.assertIsNone(find_longest_lived_storm(storms))

    def test_strongest_landfall_picks_highest_category(self):
        result = find_strongest_landfall(self._make_storms())
        self.assertEqual(result['name'], 'Willa')
        self.assertEqual(result['category'], 'Cat 5')
        self.assertEqual(result['location'], 'Sinaloa')
        self.assertEqual(result['tied_count'], 0)

    def test_strongest_landfall_counts_ties(self):
        storms = self._make_storms() + [finalize_storm({
            'id': 'EP102018', 'name': 'Vito', 'year': 2018,
            'max_wind': 140, 'wind_readings': [140],
            'start_date': datetime(2018, 10, 1), 'end_date': datetime(2018, 10, 3),
            'landfall': [('Jalisco', 'Cat 5')],
        })]
        result = find_strongest_landfall(storms)
        self.assertEqual(result['tied_count'], 1)

    def test_strongest_landfall_none_without_landfall_data(self):
        storms = [finalize_storm({
            'id': 'X', 'name': 'Fish', 'year': 2020, 'max_wind': 50,
            'wind_readings': [50], 'start_date': datetime(2020, 6, 1),
            'end_date': datetime(2020, 6, 3), 'landfall': [],
        })]
        self.assertIsNone(find_strongest_landfall(storms))

    def test_earliest_and_latest_forming_storm(self):
        storms = self._make_storms()
        self.assertEqual(find_earliest_forming_storm(storms)['name'], 'Ana')
        self.assertEqual(find_latest_forming_storm(storms)['name'], 'Zeta')

    def test_forming_storm_none_without_start_date(self):
        self.assertIsNone(find_earliest_forming_storm([{'start_date': None, 'formation_date': None}]))
        self.assertIsNone(find_latest_forming_storm([{'start_date': None, 'formation_date': None}]))


class TestFormationDateRecords(unittest.TestCase):
    """Earliest/latest-forming records must use the date a system first
    became a tropical/subtropical storm, not its first HURDAT2 track point
    (which can be days earlier as a low, depression, or extratropical system)."""

    class FakeTrack:
        def __init__(self, points):
            self.time = [t for t, _, _ in points]
            self.type = [ty for _, ty, _ in points]
            self.vmax = [v for _, _, v in points]

    # Real HURDAT2 track for Alex (AL012016): extratropical from Jan 7,
    # subtropical storm at 1800 UTC Jan 12, hurricane at 1200 UTC Jan 14.
    ALEX_2016 = [
        (datetime(2016, 1, 7, 0), 'EX', 40),
        (datetime(2016, 1, 10, 0), 'EX', 45),
        (datetime(2016, 1, 12, 12), 'EX', 45),
        (datetime(2016, 1, 12, 18), 'SS', 45),
        (datetime(2016, 1, 14, 12), 'HU', 75),
    ]

    def _storm(self, name, year, start, formation, max_wind=50):
        return finalize_storm({
            'id': f'{name}{year}', 'name': name, 'year': year,
            'max_wind': max_wind, 'wind_readings': [max_wind],
            'start_date': start, 'end_date': start + timedelta(days=5),
            'formation_date': formation, 'landfall': [],
        })

    def test_alex_2016_formation_is_first_subtropical_point(self):
        formed = _first_tropical_storm_time(self.FakeTrack(self.ALEX_2016))
        self.assertEqual(formed, datetime(2016, 1, 12, 18))

    def test_td_only_track_has_no_formation(self):
        track = self.FakeTrack([(datetime(2015, 12, 31, 0), 'TD', 30),
                                (datetime(2015, 12, 31, 6), 'LO', 25)])
        self.assertIsNone(_first_tropical_storm_time(track))

    def test_earliest_forming_uses_formation_date(self):
        # Alex's track starts Jan 7 but it formed Jan 12; the record must
        # report the formation date, not the track start.
        alex = self._storm('Alex', 2016, datetime(2016, 1, 7), datetime(2016, 1, 12, 18))
        ana = self._storm('Ana', 2003, datetime(2003, 4, 18), datetime(2003, 4, 20, 6))
        self.assertEqual(find_earliest_forming_storm([ana, alex])['name'], 'Alex')
        self.assertEqual(find_earliest_forming_storm([ana, alex])['formation_date'],
                         datetime(2016, 1, 12, 18))

    def test_forming_records_skip_depressions_and_unnamed(self):
        # "Nine" (CP092015) was a depression on Dec 31 that never became a
        # storm; an unnamed subtropical storm isn't a named storm.
        omeka = self._storm('Omeka', 2010, datetime(2010, 12, 16), datetime(2010, 12, 18, 12))
        nine = self._storm('Nine', 2015, datetime(2015, 12, 27), None, max_wind=30)
        unnamed = self._storm('Unnamed', 2023, datetime(2023, 1, 15), datetime(2023, 1, 16, 12))
        storms = [omeka, nine, unnamed]
        self.assertEqual(find_latest_forming_storm(storms)['name'], 'Omeka')
        self.assertEqual(find_earliest_forming_storm(storms)['name'], 'Omeka')

    def test_yearly_named_storm_count_excludes_depressions(self):
        storms = [self._storm('Alex', 2004, datetime(2004, 7, 31), datetime(2004, 8, 1)),
                  self._storm('Ten', 2004, datetime(2004, 9, 7), None, max_wind=30)]
        self.assertEqual(calculate_yearly_stats(storms)[2004]['named_storms'], 1)

    def test_same_date_named_count_uses_formation_date(self):
        # A system tracked from Jun 25 that only became a storm Jul 2 had not
        # "formed" as of Jun 28; a depression never counts.
        storms = []
        for year in (2023, 2024):
            storms.append(self._storm('Late', year, datetime(year, 6, 25), datetime(year, 7, 2)))
            storms.append(self._storm('Td', year, datetime(year, 6, 5), None, max_wind=30))
            storms.append(self._storm('Early', year, datetime(year, 6, 10), datetime(year, 6, 11)))
        result = calculate_same_date_stats(storms, 'atlantic', datetime(2026, 6, 28))
        self.assertEqual(result['avg_named'], 1.0)


class TestRecordsInPlay(unittest.TestCase):
    """calculate_records_in_play(): records the current season is setting
    or close to, versus completed seasons. History only."""

    def _storm(self, year, name, start, days, ace, hu=None, major=None):
        wind = 100 if major else 70 if hu else 45
        return {
            'id': f'{name}{year}', 'name': name, 'year': year, 'max_wind': wind,
            'category': 'Cat 3' if major else 'Cat 1' if hu else 'TS',
            'is_major': bool(major), 'ace': ace,
            'start_date': start, 'end_date': start + timedelta(days=days),
            'formation_date': start, 'hurricane_date': hu, 'major_date': major,
            'landfall': [],
        }

    def _history(self):
        # First hurricanes Aug 1 (2023), Sep 11 (2024), Sep 11 (2025: tie).
        return [
            self._storm(2023, 'Arlene', datetime(2023, 7, 25), 10, 30,
                        hu=datetime(2023, 8, 1), major=datetime(2023, 8, 3)),
            self._storm(2024, 'Gustav', datetime(2024, 9, 5), 10, 20, hu=datetime(2024, 9, 11, 12)),
            self._storm(2025, 'Humberto', datetime(2025, 9, 1), 20, 40,
                        hu=datetime(2025, 9, 11, 12), major=datetime(2025, 9, 21)),
        ]

    def _titles(self, records):
        return {(r['status'], r['title']) for r in records}

    def test_no_hurricane_after_record_date_is_a_record(self):
        storms = self._history() + [self._storm(2026, 'Arthur', datetime(2026, 8, 1), 3, 2)]
        records = calculate_records_in_play(storms, 'atlantic', 2, datetime(2026, 9, 26))
        hu = next(r for r in records if 'first hurricane' in r['title'])
        self.assertEqual(hu['status'], 'set')
        self.assertIn('Gustav (2024) and Humberto (2025)', hu['detail'])
        self.assertIn('September 11', hu['detail'])
        # 2024 had no major; latest first major was Sep 21 (2025)
        major = next(r for r in records if 'first major' in r['title'])
        self.assertEqual(major['status'], 'set')
        self.assertIn('2024 had none at all', major['detail'])

    def test_no_hurricane_shortly_before_record_date_is_in_play(self):
        storms = self._history()
        records = calculate_records_in_play(storms, 'atlantic', 0, datetime(2026, 9, 1))
        hu = next(r for r in records if 'first hurricane' in r['title'])
        self.assertEqual(hu['status'], 'in_play')
        self.assertIn('10 days from now', hu['detail'])

    def test_season_with_an_early_hurricane_shows_nothing_for_it(self):
        storms = self._history() + [self._storm(2026, 'Bertha', datetime(2026, 7, 1), 5, 10,
                                                hu=datetime(2026, 7, 3), major=datetime(2026, 7, 4))]
        records = calculate_records_in_play(storms, 'atlantic', 10, datetime(2026, 9, 26))
        self.assertFalse(any('first' in r['title'] for r in records))

    def test_late_first_hurricane_that_formed_is_a_record(self):
        storms = self._history() + [self._storm(2026, 'Cristobal', datetime(2026, 9, 20), 3, 5,
                                                hu=datetime(2026, 9, 22))]
        records = calculate_records_in_play(storms, 'atlantic', 5, datetime(2026, 9, 26))
        hu = next(r for r in records if 'first hurricane' in r['title'])
        self.assertEqual(hu['status'], 'set')
        self.assertIn('September 22', hu['detail'])

    def test_lowest_and_highest_ace_for_the_date(self):
        storms = self._history()
        low = calculate_records_in_play(storms, 'atlantic', 1.0, datetime(2026, 9, 26))
        self.assertIn(('set', 'Lowest ACE for the date since 1991'), self._titles(low))
        high = calculate_records_in_play(storms, 'atlantic', 55.0, datetime(2026, 9, 26))
        self.assertIn(('set', 'Most ACE for the date since 1991'), self._titles(high))
        self.assertNotIn(('set', 'Lowest ACE for the date since 1991'), self._titles(high))

    def test_ace_for_date_is_skipped_early_in_season(self):
        records = calculate_records_in_play(self._history(), 'atlantic', 0, datetime(2026, 6, 10))
        self.assertFalse(any('ACE for the date' in r['title'] for r in records))

    def test_fastest_to_100_ace(self):
        storms = [self._storm(2024, 'Beryl', datetime(2024, 7, 1), 10, 110, hu=datetime(2024, 7, 2)),
                  self._storm(2025, 'Erin', datetime(2025, 8, 1), 10, 120, hu=datetime(2025, 8, 2))]
        in_play = calculate_records_in_play(storms, 'atlantic', 80, datetime(2026, 7, 5))
        self.assertIn(('in_play', 'Fastest to 100 ACE'), self._titles(in_play))
        current = [self._storm(2026, 'Ana', datetime(2026, 6, 20), 10, 105, hu=datetime(2026, 6, 21))]
        done = calculate_records_in_play(storms + current, 'atlantic', 105, datetime(2026, 7, 5))
        self.assertIn(('set', 'Fastest to 100 ACE since 1991'), self._titles(done))

    def test_empty_history_returns_no_records(self):
        self.assertEqual(calculate_records_in_play([], 'atlantic', 10), [])

    def test_watch_window_boundary(self):
        # Latest first hurricane in the fixture is Sep 11; the panel starts
        # watching RECORD_WATCH_DAYS (14) days before, and not a day earlier.
        self.assertEqual(RECORD_WATCH_DAYS, 14)
        on_edge = calculate_records_in_play(self._history(), 'atlantic', 0, datetime(2026, 8, 28))
        hu = next(r for r in on_edge if 'first hurricane' in r['title'])
        self.assertEqual(hu['status'], 'in_play')
        self.assertIn('14 days from now', hu['detail'])
        outside = calculate_records_in_play(self._history(), 'atlantic', 0, datetime(2026, 8, 27))
        self.assertFalse(any('first hurricane' in r['title'] for r in outside))

    def test_one_day_left_is_singular(self):
        records = calculate_records_in_play(self._history(), 'atlantic', 0, datetime(2026, 9, 10))
        hu = next(r for r in records if 'first hurricane' in r['title'])
        self.assertIn('1 day from now', hu['detail'])

    def test_panel_is_empty_in_january(self):
        self.assertEqual(calculate_records_in_play(self._history(), 'atlantic', 0, datetime(2026, 1, 15)), [])

    def test_date_reached_ace(self):
        storms = [self._storm(2025, 'Erin', datetime(2025, 8, 1), 10, 120)]
        reached = _date_reached_ace(storms, 2025, 100)
        self.assertIsNotNone(reached)
        self.assertTrue(datetime(2025, 8, 1) <= reached <= datetime(2025, 8, 11))
        self.assertLess(_date_reached_ace(storms, 2025, 50), reached)
        self.assertIsNone(_date_reached_ace(storms, 2025, 200))
        self.assertIsNone(_date_reached_ace([], 2025, 1))

    def test_panel_html_escapes_and_hides_when_empty(self):
        self.assertEqual(_records_in_play_html([]), '')
        html = _records_in_play_html([{'status': 'set', 'title': 'T', 'detail': '<b>x</b>'}])
        self.assertIn('Records in Play', html)
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', html)
        self.assertIn('not a forecast', html)


class TestStormReportLinks(unittest.TestCase):
    """Per-storm NHC Tropical Cyclone Report links from NHC's report index."""

    INDEX = '''<?xml version="1.0"?><StormReportInfo>
      <row><StormName>Guillermo (Pacific)</StormName>
        <StormReportURL>https://www.nhc.noaa.gov/archive/storm_wallets/epacific/ep1991-prelim/guillerm/</StormReportURL>
        <Year>1991</Year><Basin>Pacific</Basin></row>
      <row><StormName>Unnamed (Atlantic)</StormName>
        <StormReportURL>https://www.nhc.noaa.gov/archive/storm_wallets/atlantic/atl1991-prelim/unnamed/</StormReportURL>
        <Year>1991</Year><Basin>Atlantic</Basin></row>
      <row><StormName>Hurricane Andrew (Atlantic)</StormName>
        <StormReportURL>https://www.nhc.noaa.gov/1992andrew.html</StormReportURL>
        <Year>1992</Year><Basin>Atlantic</Basin></row>
      <row><StormName>Hurricane Katrina (Atlantic)</StormName>
        <StormReportURL>https://www.nhc.noaa.gov/data/tcr/AL122005_Katrina.pdf</StormReportURL>
        <Year>2005</Year><Basin>Atlantic</Basin></row>
      <row><StormName>Hurricane Bonnie (Atlantic)</StormName>
        <StormReportURL>https://www.nhc.noaa.gov/data/tcr/AL022022_EP042022_Bonnie.pdf</StormReportURL>
        <Year>2022</Year><Basin>Atlantic</Basin></row>
      <row><StormName>Hurricane Otto (Atlantic)</StormName>
        <StormReportURL>https://www.nhc.noaa.gov/data/tcr/AL162016_Otto.pdf</StormReportURL>
        <Year>2016</Year><Basin>Atlantic</Basin></row>
      <row><StormName>Bad (Atlantic)</StormName>
        <StormReportURL>https://example.com/x.pdf</StormReportURL>
        <Year>2020</Year><Basin>Atlantic</Basin></row>
    </StormReportInfo>'''

    def _rows(self):
        return parse_tcr_index(self.INDEX)

    def test_parse_keeps_only_nhc_urls(self):
        rows = self._rows()
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]['basin'], 'pacific')
        self.assertEqual(rows[0]['year'], 1991)

    def test_pdf_reports_match_by_storm_id(self):
        m = match_tcr_reports(self._rows(), [{'id': 'AL122005', 'name': 'Katrina', 'year': 2005}], 'atlantic')
        self.assertEqual(m['AL122005'], 'https://www.nhc.noaa.gov/data/tcr/AL122005_Katrina.pdf')

    def test_crossover_storm_matches_either_id(self):
        # Bonnie 2022 is EP042022 in the Pacific dataset; Otto 2016 is
        # EP222016 there but its report is only filed as AL162016.
        storms = [{'id': 'EP042022', 'name': 'Bonnie', 'year': 2022},
                  {'id': 'EP222016', 'name': 'Otto', 'year': 2016}]
        m = match_tcr_reports(self._rows(), storms, 'pacific')
        self.assertIn('AL022022_EP042022_Bonnie.pdf', m['EP042022'])
        self.assertIn('AL162016_Otto.pdf', m['EP222016'])

    def test_1991_storm_wallets_match_by_truncated_name(self):
        storms = [{'id': 'EP081991', 'name': 'Guillermo', 'year': 1991},
                  {'id': 'AL011991', 'name': 'Unnamed', 'year': 1991}]
        self.assertIn('guillerm', match_tcr_reports(self._rows(), storms, 'pacific')['EP081991'])
        self.assertIn('atl1991-prelim/unnamed', match_tcr_reports(self._rows(), storms, 'atlantic')['AL011991'])

    def test_name_fallback_and_missing_reports(self):
        storms = [{'id': 'AL041992', 'name': 'Andrew', 'year': 1992},
                  {'id': 'AL171995', 'name': 'Opal', 'year': 1995},
                  {'id': 'AL212005', 'name': 'Unnamed', 'year': 2005}]
        m = match_tcr_reports(self._rows(), storms, 'atlantic')
        self.assertEqual(m, {'AL041992': 'https://www.nhc.noaa.gov/1992andrew.html'})

    def test_storm_list_shows_report_icon_only_when_known(self):
        storms_list = [{'id': 'AL122005', 'name': 'Katrina', 'ace': 20.0, 'category': 'Cat 5',
                        'max_wind': 150, 'landfall': []},
                       {'id': 'AL171995', 'name': 'Opal', 'ace': 10.0, 'category': 'Cat 4',
                        'max_wind': 130, 'landfall': []}]
        html = _year_storm_list_html(storms_list, {'AL122005': 'https://www.nhc.noaa.gov/data/tcr/AL122005_Katrina.pdf'})
        self.assertEqual(html.count('class="ys-tcr"'), 1)
        self.assertIn('aria-label="NHC report for Katrina"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        self.assertNotIn('ys-tcr', _year_storm_list_html(storms_list))


class TestCleanLandfalls(unittest.TestCase):
    """Landfall lists must not repeat a place, or repeat a name that is both
    the region and the country (e.g. 'Puerto Rico, Puerto Rico')."""

    def test_region_equal_to_country_is_collapsed(self):
        self.assertEqual(_clean_landfalls([('Puerto Rico, Puerto Rico', 'TD')]),
                         [('Puerto Rico', 'TD')])

    def test_repeat_location_keeps_strongest_category_in_first_position(self):
        # Irma 2017 crossed Florida twice (Cat 4, then Cat 3).
        raw = [['Camagüey, Cuba', 'Cat 5'], ['Florida', 'Cat 4'], ['Florida', 'Cat 3']]
        self.assertEqual(_clean_landfalls(raw),
                         [('Camagüey, Cuba', 'Cat 5'), ('Florida', 'Cat 4')])
        raw = [['Belize, Belize', 'TS'], ['Tamaulipas, Mexico', 'Cat 1'], ['Belize, Belize', 'Cat 1']]
        self.assertEqual(_clean_landfalls(raw),
                         [('Belize', 'Cat 1'), ('Tamaulipas, Mexico', 'Cat 1')])

    def test_empty_and_distinct_lists_are_unchanged(self):
        self.assertEqual(_clean_landfalls([]), [])
        self.assertEqual(_clean_landfalls([('Texas', 'Cat 4'), ('Louisiana', 'TS')]),
                         [('Texas', 'Cat 4'), ('Louisiana', 'TS')])


class TestStormsOnThisDay(unittest.TestCase):
    """Tests for find_storms_on_this_day() — the 'on this day' history insight."""

    def _make_storms(self):
        return [
            # Active Aug 23 - Aug 30, 2005 — should match Aug 25 and Aug 30, not Sep 1
            finalize_storm({
                'id': 'AL122005', 'name': 'Katrina', 'year': 2005,
                'max_wind': 150, 'wind_readings': [150, 150],
                'start_date': datetime(2005, 8, 23),
                'end_date':   datetime(2005, 8, 30),
                'landfall':   [],
            }),
            # Active Aug 24 - Aug 26, 2012 — weaker storm, also matches Aug 25
            finalize_storm({
                'id': 'AL092012', 'name': 'Nadine', 'year': 2012,
                'max_wind': 70, 'wind_readings': [70, 70],
                'start_date': datetime(2012, 8, 24),
                'end_date':   datetime(2012, 8, 26),
                'landfall':   [],
            }),
            # Active Aug 25, 2026 (current year) — must be excluded as "current season"
            finalize_storm({
                'id': 'AL012026', 'name': 'Arthur', 'year': 2026,
                'max_wind': 40, 'wind_readings': [40, 40],
                'start_date': datetime(2026, 8, 25),
                'end_date':   datetime(2026, 8, 25),
                'landfall':   [],
            }),
        ]

    def test_matches_storms_active_on_target_date(self):
        storms = self._make_storms()
        result = find_storms_on_this_day(storms, datetime(2026, 8, 25))
        names = [s['name'] for s in result]
        self.assertIn('Katrina', names)
        self.assertIn('Nadine', names)

    def test_excludes_dates_outside_storm_range(self):
        storms = self._make_storms()
        result = find_storms_on_this_day(storms, datetime(2026, 9, 1))
        self.assertEqual(result, [])

    def test_excludes_current_year(self):
        storms = self._make_storms()
        result = find_storms_on_this_day(storms, datetime(2026, 8, 25))
        names = [s['name'] for s in result]
        self.assertNotIn('Arthur', names)

    def test_sorted_by_ace_descending(self):
        storms = self._make_storms()
        result = find_storms_on_this_day(storms, datetime(2026, 8, 25))
        aces = [s['ace'] for s in result]
        self.assertEqual(aces, sorted(aces, reverse=True))
        self.assertEqual(result[0]['name'], 'Katrina')

    def test_missing_dates_are_skipped(self):
        storms = self._make_storms()
        storms.append({'id': 'X', 'name': 'NoDate', 'year': 2020,
                        'start_date': None, 'end_date': None, 'ace': 0})
        result = find_storms_on_this_day(storms, datetime(2026, 8, 25))
        names = [s['name'] for s in result]
        self.assertNotIn('NoDate', names)


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
                'formation_date': datetime(2026, 6, 15),
                'end_date':   datetime(2026, 6, 18),
                'landfall':   [('Texas', 'TS')],
            }),
            finalize_storm({
                'id': 'AL012005', 'name': 'Katrina', 'year': 2005,
                'max_wind': 150, 'wind_readings': [150, 150, 130, 100],
                'start_date': datetime(2005, 8, 23),
                'formation_date': datetime(2005, 8, 23),
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

    def test_wind_unit_toggle_present(self):
        """Dashboard renders the wind unit toggle button and JS, and marks
        every wind-speed display site with a canonical data-kt value so
        the toggle can convert them client-side."""
        basin_data = self._make_basin_data()
        result = generate_dashboard_html(basin_data)
        self.assertIn('id="unitBtn"', result)
        self.assertIn('function toggleWindUnit()', result)
        self.assertIn('function applyWindUnit()', result)
        # Storm table cell (bare number, unit shown via column header)
        self.assertIn("class='wind-val' data-kt='40'", result)
        # Peak Intensity meta-box (number + unit inline)
        self.assertIn('class="wind-val-unit" data-kt="40"', result)
        # Sortable column header carries labels for all 3 units
        self.assertIn('data-mph-label="Wind (mph)"', result)
        # Per-point intensity bar tooltip data, used to rebuild the title on toggle
        self.assertIn('data-wind-kt="40"', result)

    def test_history_html_generates(self):
        """generate_history_html() runs without error and returns non-empty HTML."""
        basin_data = self._make_basin_data()
        result = generate_history_html(basin_data)
        self.assertIsInstance(result, str)
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('All Seasons', result)
        self.assertIn('2005', result)

    def test_records_html_generates(self):
        """generate_records_html() runs without error, returns non-empty
        HTML, and surfaces records derived from the fixture's storms (#63)."""
        basin_data = self._make_basin_data()
        result = generate_records_html(basin_data)
        self.assertIsInstance(result, str)
        self.assertIn('<!DOCTYPE html>', result)
        # Katrina (2005) is the fixture's highest-ACE and only-landfall storm
        self.assertIn('Katrina', result)
        self.assertIn('Records Since', result)
        self.assertIn('Formed August 23', result)

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


class TestHistoryDecadeFilterAndReports(unittest.TestCase):
    """History page decade filter (#59) and NHC storm report links (#50)."""

    def _history(self, basin_key='atlantic'):
        basin_data = TestHTMLGeneration()._make_basin_data()
        basin_data[0]['basin_key'] = basin_key
        basin_data[0]['yearly_totals'] = {1995: 227.1, 2005: 245.0, 2024: 161.6, 2025: 130.8}
        return generate_history_html(basin_data)

    def test_decade_label(self):
        self.assertEqual(_decade_label(1991), '1990s')
        self.assertEqual(_decade_label(2000), '2000s')
        self.assertEqual(_decade_label(2029), '2020s')

    def test_decade_buttons_match_seasons_present(self):
        """One button per decade that has seasons (plus All), and no
        buttons for decades with no data."""
        result = self._history()
        self.assertIn('class="decade-filter" role="group"', result)
        self.assertIn('data-decade="all" aria-pressed="true"', result)
        for dec in ('1990s', '2000s', '2020s'):
            self.assertIn(f'data-decade="{dec}" aria-pressed="false"', result)
        self.assertNotIn('data-decade="2010s"', result)

    def test_rows_tagged_with_decade(self):
        result = self._history()
        self.assertIn('id="atlantic-yr-1995" data-decade="1990s"', result)
        self.assertIn('id="atlantic-yr-2026" data-decade="2020s"', result)

    def test_filter_js_and_shareable_hash(self):
        """Filter JS is present and the decade is read from / written to
        the URL hash alongside the basin (e.g. #pacific&decade=2010s)."""
        result = self._history()
        self.assertIn('function filterDecade(dec)', result)
        self.assertIn("'&decade='+_decade", result)
        self.assertIn("p.indexOf('decade=')===0", result)

    def test_atlantic_report_links(self):
        result = self._history()
        self.assertIn('https://www.nhc.noaa.gov/data/tcr/index.php?season=2005&amp;basin=atl', result)
        self.assertIn('NHC storm reports for 1995', result)
        self.assertNotIn('basin=epac', result)

    def test_pacific_report_links_cover_both_basins(self):
        """The E/C Pacific tab links both NHC (epac) and CPHC (cpac) reports."""
        result = self._history('pacific')
        self.assertIn('index.php?season=2005&amp;basin=epac', result)
        self.assertIn('index.php?season=2005&amp;basin=cpac', result)
        self.assertNotIn('basin=atl"', result)

    def test_active_season_report_note(self):
        """Only the in-progress season gets the 'still filling in' note."""
        self.assertIn('still filling in', _nhc_tcr_links_html(2026, 'atlantic', is_active=True))
        self.assertNotIn('still filling in', _nhc_tcr_links_html(2005, 'atlantic'))

    def test_unknown_basin_has_no_report_links(self):
        self.assertEqual(_nhc_tcr_links_html(2005, 'westpac'), '')


class TestPageTitlesAndShareMeta(unittest.TestCase):
    """Page titles carry the season year; share metadata matches the
    1200x630 preview card and the 3-hour publish schedule."""

    def _pages(self):
        basin_data = TestHTMLGeneration()._make_basin_data()
        return {
            'dashboard': generate_dashboard_html(basin_data),
            'history': generate_history_html(basin_data),
            'records': generate_records_html(basin_data),
        }

    def test_titles_include_season_year(self):
        pages = self._pages()
        self.assertIn('<title>2026 Hurricane Season ACE Tracker: Atlantic &amp; East Pacific | aceofcanes.com</title>',
                      pages['dashboard'])
        self.assertIn('<title>Hurricane Season History (1991–2026): ACE by Year | aceofcanes.com</title>',
                      pages['history'])
        self.assertIn('<title>Hurricane Records 1991–2026: Atlantic &amp; East Pacific | aceofcanes.com</title>',
                      pages['records'])

    def test_share_meta_and_update_cadence(self):
        for name, html in self._pages().items():
            with self.subTest(page=name):
                self.assertNotIn('every 6 hours', html)
                self.assertIn('<meta property="og:image:width" content="1200">', html)
                self.assertIn('<meta property="og:image:height" content="630">', html)
                self.assertIn('og:image:alt', html)

    def test_logo_does_not_leak_into_heading_text(self):
        # alt="ACE" made screen readers and search snippets read the h1 as
        # "ACE Hurricane ACE Dashboard".
        for name, html in self._pages().items():
            with self.subTest(page=name):
                self.assertNotIn('alt="ACE"', html)
                self.assertIn('class="logo" alt="" aria-hidden="true"', html)

    def test_share_image_is_1200x630(self):
        import os
        import struct
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ace_preview.png')
        with open(path, 'rb') as f:
            header = f.read(24)
        self.assertEqual(header[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(struct.unpack('>II', header[16:24]), (1200, 630))


class TestWhatIsAcePage(unittest.TestCase):
    """The standalone What-is-ACE page: formula, NOAA thresholds,
    calculator, facts from site data, and links from every page's nav."""

    def test_page_has_formula_thresholds_and_calculator(self):
        html = generate_about_html(TestHTMLGeneration()._make_basin_data())
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('ACE = Σ V<sub>max</sub>² × 10⁻⁴', html)
        for text in ('&lt; 73', '73–126', '126–159', '159+'):
            self.assertIn(text, html)
        self.assertIn('id="calcWinds"', html)
        self.assertIn('CALC_MIN_KT=34', html)
        self.assertIn('rel="canonical" href="https://aceofcanes.com/what-is-ace.html"', html)

    def test_fun_facts_come_from_site_data(self):
        html = generate_about_html(TestHTMLGeneration()._make_basin_data())
        # Fixture: completed seasons 2005 (245.0), 2024, 2025; Katrina top storm
        self.assertIn('<b>2005</b> at <b>245.0 ACE</b>', html)
        self.assertIn('Katrina (2005)', html)

    def test_page_renders_without_basin_data(self):
        html = generate_about_html([])
        self.assertIn('id="calculator"', html)
        self.assertNotIn("From this site's data", html)

    def test_explainer_link_uses_accent_color(self):
        # Unstyled, the link fell back to the browser's dark purple visited
        # color, which is nearly invisible on the dark theme.
        basin_data = TestHTMLGeneration()._make_basin_data()
        for gen in (generate_dashboard_html, generate_history_html):
            with self.subTest(page=gen.__name__):
                self.assertIn('.ace-explain p a, .ace-explain p a:visited { color:var(--accent);', gen(basin_data))

    def test_every_page_links_to_it(self):
        basin_data = TestHTMLGeneration()._make_basin_data()
        for gen in (generate_dashboard_html, generate_history_html, generate_records_html):
            with self.subTest(page=gen.__name__):
                self.assertIn('href="what-is-ace.html"', gen(basin_data))


class TestLandfallAceShare(unittest.TestCase):
    """Share of season ACE from landfalling storms vs. fish storms."""

    STORMS = [
        {'name': 'Hitter', 'ace': 30.0, 'max_wind': 120, 'landfall': [('Florida', 'Cat 3')]},
        {'name': 'Fish', 'ace': 10.0, 'max_wind': 80, 'landfall': []},
        {'name': 'Td', 'ace': 0.0, 'max_wind': 30, 'landfall': [('Texas', 'TD')]},
    ]

    def test_split_and_counts_ignore_depressions(self):
        self.assertEqual(landfall_ace_share(self.STORMS),
                         {'landfall_pct': 75, 'fish_pct': 25, 'landfall_count': 1, 'fish_count': 1})

    def test_depression_strength_landfall_is_not_landfalling(self):
        # A storm that only crossed land as a depression (Boris 2026 at
        # Guerrero) stayed a fish storm for the share; any TS+ landfall counts.
        storms = [
            {'name': 'Crosser', 'ace': 20.0, 'max_wind': 70, 'landfall': [('Guerrero, Mexico', 'TD')]},
            {'name': 'Hitter', 'ace': 20.0, 'max_wind': 70,
             'landfall': [['Cuba', 'TD'], ['Florida', 'TS']]},
        ]
        self.assertEqual(landfall_ace_share(storms),
                         {'landfall_pct': 50, 'fish_pct': 50, 'landfall_count': 1, 'fish_count': 1})

    def test_no_ace_returns_none(self):
        self.assertIsNone(landfall_ace_share([]))
        self.assertIsNone(landfall_ace_share([self.STORMS[2]]))

    def test_average_uses_completed_seasons_only(self):
        stats = {
            2024: {'storms_list': self.STORMS},                                      # 75%
            2025: {'storms_list': [dict(self.STORMS[1])]},                          # 0%
            2026: {'storms_list': [dict(self.STORMS[0])]},                          # current, excluded
        }
        self.assertEqual(average_landfall_share(stats, 2026), 38)
        self.assertIsNone(average_landfall_share({}, 2026))

    def test_dashboard_insight_and_history_panel(self):
        basin_data = TestHTMLGeneration()._make_basin_data()
        bd = basin_data[0]
        bd['yearly_stats'] = calculate_yearly_stats(bd['historical_storms'])
        insights = generate_insights('atlantic', bd['current'], bd['yearly_totals'],
                                     bd['historical_storms'], bd['yearly_stats'])
        share = [i for i in insights if i.startswith('🏝️ Landfall share')]
        self.assertEqual(len(share), 1)
        self.assertIn('of season ACE came from the', share[0])
        history = generate_history_html(basin_data)
        self.assertIn('class="yr-lfshare"', history)
        self.assertIn('of a season\'s ACE came from storms that made landfall', history)


class TestRankCurrentSeason(unittest.TestCase):
    """Season ranking must not double-count the in-progress year (Sprint 0 fix)."""

    def test_current_year_present_is_not_double_counted(self):
        # parse_hurdat2 loads through the present, so yearly_totals already
        # holds the current year — the old code appended it again.
        totals = {2024: 100.0, 2025: 50.0, 2026: 10.0}
        rank, total_seasons = rank_current_season(totals, 2026, 10.0)
        self.assertEqual(total_seasons, 3)
        self.assertEqual(rank, 3)

    def test_live_total_overrides_historical_entry(self):
        totals = {2024: 100.0, 2025: 50.0, 2026: 60.0}
        rank, total_seasons = rank_current_season(totals, 2026, 120.0)
        self.assertEqual(total_seasons, 3)
        self.assertEqual(rank, 1)

    def test_current_year_absent_is_added_once(self):
        totals = {2024: 100.0, 2025: 50.0}
        rank, total_seasons = rank_current_season(totals, 2026, 75.0)
        self.assertEqual(total_seasons, 3)
        self.assertEqual(rank, 2)


class TestAceFromWinds(unittest.TestCase):
    """Single ACE formula shared by historical and current-season paths."""

    def test_matches_finalize_storm(self):
        winds = [35, 50, 65, 100]
        storm = finalize_storm({
            'wind_readings': winds, 'max_wind': 100,
            'start_date': None, 'end_date': None,
        })
        self.assertEqual(ace_from_winds(winds), storm['ace'])

    def test_known_value(self):
        # 50² + 50² = 5000 → 0.5 ACE
        self.assertEqual(ace_from_winds([50, 50]), 0.5)

    def test_empty_readings(self):
        self.assertEqual(ace_from_winds([]), 0.0)


class TestLandfallCacheInvalidation(unittest.TestCase):
    """Current-season landfall cache entries must refresh with new advisories."""

    def test_stale_bare_and_old_timestamped_keys_are_dropped(self):
        cache = {
            'AL012026': [('x', 'y')],              # stale legacy bare key
            'cur:AL012026:2026081000': [('a',)],   # older advisory
            'cur:AL012026:2026081512': [('b',)],   # current key — kept
            'AL012025': [('keep',)],               # different storm — kept
        }
        changed = _drop_stale_storm_keys(cache, 'AL012026', 'cur:AL012026:2026081512', 'cur')
        self.assertTrue(changed)
        self.assertEqual(set(cache), {'cur:AL012026:2026081512', 'AL012025'})

    def test_pruning_is_scoped_to_one_key_family(self):
        # A cur:-family prune must never remove geo: entries (different computation).
        cache = {
            'geo:AL012026:2026081512': [('geo',)],
            'cur:AL012026:2026081000': [('old',)],
        }
        _drop_stale_storm_keys(cache, 'AL012026', 'cur:AL012026:2026081512', 'cur')
        self.assertIn('geo:AL012026:2026081512', cache)
        self.assertNotIn('cur:AL012026:2026081000', cache)

    def test_no_change_returns_false(self):
        cache = {'cur:AL012026:2026081512': [('b',)]}
        changed = _drop_stale_storm_keys(cache, 'AL012026', 'cur:AL012026:2026081512', 'cur')
        self.assertFalse(changed)
        self.assertEqual(len(cache), 1)

    def test_last_track_stamp_formats_datetime(self):
        class FakeStorm:
            time = [datetime(2026, 8, 15, 12)]
        self.assertEqual(_last_track_stamp(FakeStorm()), '2026081512')

    def test_last_track_stamp_handles_missing_track(self):
        class Broken:
            @property
            def time(self):
                raise RuntimeError('no track')
        self.assertEqual(_last_track_stamp(Broken()), 'unknown')


class TestKeyboardAndAria(unittest.TestCase):
    """Keyboard reachability, ARIA state and focus styling on every page."""

    def _pages(self):
        basin_data = TestHTMLGeneration()._make_basin_data()
        return {
            'dashboard': generate_dashboard_html(basin_data),
            'history': generate_history_html(basin_data),
            'records': generate_records_html(basin_data),
            'what-is-ace': generate_about_html(basin_data),
        }

    def test_tooltips_do_not_add_tab_stops(self):
        # Every [data-tip] used to get tabindex=0: ~1,300 tab stops on the
        # history page (every category chip and Fish Storm label).
        for name, html in self._pages().items():
            with self.subTest(page=name):
                self.assertNotIn("setAttribute('tabindex'", html)
                self.assertNotIn('tabindex="0"', html)

    def test_sort_headers_are_buttons_with_aria_sort(self):
        pages = self._pages()
        for name, fn, n, default in (('dashboard', 'sortDash', 5, 'ACE'), ('history', 'sortHist', 9, 'Year')):
            with self.subTest(page=name):
                html = pages[name]
                self.assertNotIn('<th class="sort-th" onclick', html)
                self.assertEqual(html.count(f'<button type="button" class="sort-btn" onclick="{fn}('), n)
                self.assertIn(f'<th class="sort-th" aria-sort="descending"><button type="button" class="sort-btn" '
                              f'onclick="{fn}(this,{0 if default == "Year" else 1},\'n\')">{default} ', html)
                self.assertIn("h.setAttribute('aria-sort',asc?'ascending':'descending')", html)

    def test_toggles_and_icon_buttons_have_state_and_names(self):
        for name, html in self._pages().items():
            with self.subTest(page=name):
                self.assertIn('id="themeBtn" onclick="toggleTheme()" aria-label="Toggle light and dark theme"', html)
                self.assertIn("'Switch to dark mode':'Switch to light mode'", html)
                if name != 'what-is-ace':
                    self.assertIn('<button class="active" aria-pressed="true" onclick="show(\'atlantic\',this)">', html)
                    self.assertIn('<button aria-pressed="false" onclick="show(\'pacific\',this)">', html)
                    self.assertIn("btn.setAttribute('aria-pressed','true')", html)
        dashboard = self._pages()['dashboard']
        self.assertIn('id="unitBtn" onclick="toggleWindUnit()" title="Wind speed unit" aria-label="Wind speed unit: kt"', dashboard)
        self.assertIn("btn.setAttribute('aria-label','Wind speed unit: '+WIND_UNIT_LABELS[unit])", dashboard)

    def test_collapsed_panels_leave_the_tab_order(self):
        # max-height:0 alone left ~540 report links in collapsed season
        # panels reachable by Tab; visibility:hidden removes them, and the
        # delayed visibility transition keeps the close animation.
        pages = self._pages()
        self.assertIn('.track-panel { overflow:hidden; max-height:0; visibility:hidden;', pages['dashboard'])
        self.assertIn('.track-panel.open { max-height:1500px; visibility:visible;', pages['dashboard'])
        self.assertIn('.yr-panel { overflow:hidden; max-height:0; visibility:hidden;', pages['history'])
        self.assertIn('.yr-panel.open { max-height:2000px; visibility:visible;', pages['history'])

    def test_every_page_has_a_focus_ring(self):
        for name, html in self._pages().items():
            with self.subTest(page=name):
                self.assertIn(':focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}'
                              .replace('{{', '{').replace('}}', '}'), html)

    def test_row_buttons_expose_expanded_state(self):
        pages = self._pages()
        self.assertIn('id="trbtn-arthur" aria-expanded="false" aria-controls="trpanel-arthur"', pages['dashboard'])
        self.assertIn("btn.setAttribute('aria-expanded','true')", pages['dashboard'])
        self.assertIn('id="yrbtn-atlantic-yr-2005" aria-expanded="false" aria-controls="yrpanel-atlantic-yr-2005"',
                      pages['history'])
        self.assertIn("btn.setAttribute('aria-expanded',open?'false':'true')", pages['history'])


class TestColorContrast(unittest.TestCase):
    """Text colors defined as theme tokens meet WCAG AA (4.5:1) against the
    surfaces they sit on, computed from each page's generated CSS."""

    @staticmethod
    def _ratio(fg, bg):
        def lum(h):
            c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
        return (hi + 0.05) / (lo + 0.05)

    @staticmethod
    def _themes(html):
        import re
        dark = re.search(r':root \{(.*?)\}', html, re.S).group(1)
        light = re.search(r'\[data-theme="light"\] \{(.*?)\}', html, re.S).group(1)
        parse = lambda block: dict(re.findall(r'--([\w-]+):(#[0-9a-fA-F]{6})', block))
        return {'dark': parse(dark), 'light': parse(light)}

    def test_muted_text_on_page_surfaces(self):
        pages = TestKeyboardAndAria()._pages()
        for name, html in pages.items():
            for theme, tok in self._themes(html).items():
                for surface in ('card', 'box', 'sources-bg', 'bg'):
                    if surface not in tok:
                        continue
                    with self.subTest(page=name, theme=theme, surface=surface):
                        self.assertGreaterEqual(self._ratio(tok['muted'], tok[surface]), 4.5)
                if 'muted-dark' in tok and 'sources-bg' in tok:
                    with self.subTest(page=name, theme=theme, token='muted-dark'):
                        self.assertGreaterEqual(self._ratio(tok['muted-dark'], tok['sources-bg']), 4.5)

    def test_classification_badges_with_white_text(self):
        pages = TestKeyboardAndAria()._pages()
        for name in ('history', 'what-is-ace'):
            for theme, tok in self._themes(pages[name]).items():
                for badge in ('badge-extreme', 'badge-above', 'badge-near', 'badge-below'):
                    if badge not in tok:
                        continue
                    with self.subTest(page=name, theme=theme, badge=badge):
                        self.assertGreaterEqual(self._ratio('#ffffff', tok[badge]), 4.5)
class TestDataFreshness(unittest.TestCase):
    """The dashboard says how current its storm data is, not only when the
    page was built: a stale page must look stale."""

    class _Storm:
        def __init__(self, *times):
            self.time = list(times)

    def test_latest_track_time_is_newest_point_across_storms(self):
        from datetime import timezone
        storms = [
            self._Storm(datetime(2026, 9, 20, 0), datetime(2026, 9, 26, 18)),
            self._Storm(datetime(2026, 9, 25, 6), datetime(2026, 9, 27, 0, tzinfo=timezone.utc)),
            self._Storm(),  # no track points
        ]
        self.assertEqual(latest_track_time(storms), '2026-09-27T00:00:00Z')

    def test_latest_track_time_none_without_tracks(self):
        self.assertIsNone(latest_track_time([]))
        self.assertIsNone(latest_track_time([self._Storm()]))

    def test_data_as_of_line(self):
        line = _data_as_of_html('2026-09-27T00:00:00Z')
        self.assertIn('Best-track data as of <time datetime="2026-09-27T00:00:00Z">Sep 27, 2026 00:00 UTC</time>', line)
        self.assertIn('class="rel-time" data-ts="2026-09-27T00:00:00Z"', line)
        self.assertNotIn('outlook', line)

    def test_data_as_of_line_with_outlook_time(self):
        line = _data_as_of_html('2026-09-27T00:00:00Z', 'Sat, 27 Sep 2026 17:40:00 GMT')
        self.assertIn('NHC outlook issued <time datetime="2026-09-27T17:40:00Z">Sep 27, 2026 17:40 UTC</time>', line)

    def test_data_as_of_line_omitted_without_times(self):
        self.assertEqual(_data_as_of_html(None), '')
        self.assertEqual(_data_as_of_html(None, 'not a date'), '')

    def test_dashboard_shows_data_time_and_moves_build_time_to_footer(self):
        basin_data = TestHTMLGeneration()._make_basin_data()
        basin_data[0]['current']['data_as_of'] = '2026-06-18T00:00:00Z'
        html = generate_dashboard_html(basin_data)
        self.assertIn('Best-track data as of <time datetime="2026-06-18T00:00:00Z">', html)
        self.assertIn('function _relTimes()', html)
        self.assertNotIn('<div class="updated">', html)
        footer = html[html.index('<div class="sources">'):]
        self.assertIn('Page built ', footer)
        self.assertIn('Updates every 3 hours.', footer)


class TestIntensityBarLabel(unittest.TestCase):
    """The color-only intensity bar carries its stage sequence as text."""

    def test_label_collapses_repeated_stages(self):
        pts = [{'status': s, 'wind': w, 'time': 't'} for s, w in
               [('TD', 30), ('TS', 40), ('TS', 50), ('HU', 70), ('HU', 100), ('HU', 70), ('TS', 45)]]
        html = _intensity_bar_html(pts)
        self.assertIn('role="img"', html)
        self.assertIn('aria-label="Intensity over time: tropical depression → tropical storm → Cat 1 → Cat 3 → Cat 1 → tropical storm"', html)

    def test_empty_track_has_no_bar(self):
        self.assertEqual(_intensity_bar_html([]), '')


class TestHonestyLabels(unittest.TestCase):
    """In-season ACE is labelled preliminary and geocoded landfalls are
    labelled estimated wherever they appear."""

    def _data(self, estimated=True):
        basin_data = TestHTMLGeneration()._make_basin_data()
        basin_data[0]['current']['storm_details']['Arthur']['landfall_estimated'] = estimated
        return basin_data

    def test_dashboard_headline_is_preliminary(self):
        html = generate_dashboard_html(self._data())
        self.assertIn('<div class="stat-label">Season ACE <span class="prelim"', html)

    def test_dashboard_marks_estimated_landfalls(self):
        html = generate_dashboard_html(self._data())
        self.assertIn('Texas (TS) <abbr class="lf-est"', html)
        self.assertIn('class="table-note"', html)

    def test_hurdat2_landfalls_not_marked_estimated(self):
        html = generate_dashboard_html(self._data(estimated=False))
        self.assertNotIn('<abbr class="lf-est"', html)
        self.assertNotIn('class="table-note"', html)

    def test_history_current_row_is_preliminary(self):
        html = generate_history_html(self._data())
        row = html[html.index('id="atlantic-yr-2026"'):]
        row = row[:row.index('</tr>')]
        self.assertIn('class="prelim"', row)
        past = html[html.index('id="atlantic-yr-2005"'):]
        self.assertNotIn('class="prelim"', past[:past.index('</tr>')])

    def test_what_is_ace_fact_is_preliminary(self):
        html = generate_about_html(self._data())
        self.assertIn('ACE</b> so far (preliminary;', html)

    def test_landfall_share_insight_labels(self):
        bd = self._data()[0]
        bd['yearly_stats'] = calculate_yearly_stats(bd['historical_storms'])
        insights = generate_insights('atlantic', bd['current'], bd['yearly_totals'],
                                     bd['historical_storms'], bd['yearly_stats'])
        share = [i for i in insights if i.startswith('🏝️ Landfall share')][0]
        self.assertTrue(share.startswith('🏝️ Landfall share (estimated):'))
        self.assertIn('made landfall at tropical-storm strength or stronger', share)

    def test_landfall_share_insight_with_no_ts_landfall(self):
        bd = self._data()[0]
        bd['current']['storm_details']['Arthur']['landfall'] = [('Guerrero, Mexico', 'TD')]
        insights = generate_insights('atlantic', bd['current'], bd['yearly_totals'],
                                     bd['historical_storms'], calculate_yearly_stats(bd['historical_storms']))
        share = [i for i in insights if i.startswith('🏝️ Landfall share')][0]
        self.assertIn(': no storm has made landfall at tropical-storm strength or stronger', share)
        self.assertIn('so 1 storm counts as a fish storm, including Arthur, '
                      'which reached Guerrero, Mexico only as a depression', share)
        self.assertNotIn('0 storms', share)

    def test_landfall_share_insight_names_depression_landfalls(self):
        bd = self._data()[0]
        bd['current']['storms']['Dolly'] = 0.5
        bd['current']['storm_details']['Dolly'] = {
            'ace': 0.5, 'max_wind': 40, 'track_points': [], 'is_active': False,
            'start_date': '7/1', 'landfall': [('Puerto Rico', 'TD')], 'landfall_estimated': True}
        bd['current']['total'] = 0.91
        insights = generate_insights('atlantic', bd['current'], bd['yearly_totals'],
                                     bd['historical_storms'], calculate_yearly_stats(bd['historical_storms']))
        share = [i for i in insights if i.startswith('🏝️ Landfall share')][0]
        self.assertIn('from the 1 storm that made landfall at tropical-storm strength or stronger', share)
        self.assertIn('from 1 fish storm, including Dolly, which reached Puerto Rico only as a depression', share)

    def test_history_panel_counts_depression_landfalls(self):
        from ace_html import _landfall_share_html
        html = _landfall_share_html([
            {'name': 'Hitter', 'ace': 30.0, 'max_wind': 120, 'landfall': [('Florida', 'Cat 3')]},
            {'name': 'Crosser', 'ace': 10.0, 'max_wind': 50, 'landfall': [['Texas', 'TD']]},
            {'name': 'Fish', 'ace': 10.0, 'max_wind': 50, 'landfall': []},
        ])
        self.assertIn('Landfalling (TS or stronger): <b>60%</b>', html)
        self.assertIn('(2, incl. 1 that reached land only as a depression)', html)


class TestGuidanceTimestamps(unittest.TestCase):
    """Relayed model tracks and the NHC cone carry the time they were issued."""

    class _Storm:
        def get_operational_forecasts(self):
            return {
                'OFCL': {
                    '2026092618': {'lat': [20.0], 'lon': [-60.0], 'fhr': [0]},
                    '2026092700': {'lat': [20.5, 21.0], 'lon': [-61.0, -62.0], 'fhr': [0, 12],
                                   'init': datetime(2026, 9, 27, 0)},
                },
                'AVNO': {'2026092606': {'lat': [20.0], 'lon': [-60.0], 'fhr': [6]}},
                'EMX': {'2026092612': {'lat': [20.0], 'lon': [-60.0], 'fhr': [-6]}},  # nothing forward
            }

    def test_spaghetti_returns_latest_cycle_per_model(self):
        tracks, cycles = _extract_spaghetti_tracks(self._Storm())
        self.assertEqual(sorted(tracks), ['AVNO', 'OFCL'])
        self.assertEqual(len(tracks['OFCL']), 2)
        self.assertEqual(cycles, {'OFCL': '2026-09-27T00:00:00Z', 'AVNO': '2026-09-26T06:00:00Z'})

    def test_spaghetti_drops_runs_far_older_than_the_newest(self):
        # HWRF and HMON stopped running for Fay 2026; Tropycal still returned
        # their last (Sep 21) runs on Sep 27, drawn beside current guidance.
        def fc(lat):
            return {'lat': [lat], 'lon': [-60.0], 'fhr': [0]}

        class Storm:
            def get_operational_forecasts(self):
                return {
                    'OFCL': {'2026092700': fc(20.0)},
                    'AVNO': {'2026092618': fc(20.1)},
                    'CMC': {'2026092600': fc(20.2)},   # exactly 24 h behind: kept
                    'UKX': {'2026092518': fc(20.3)},   # 30 h behind: dropped
                    'HWRF': {'2026092118': fc(20.4)},  # six days behind: dropped
                }
        tracks, cycles = _extract_spaghetti_tracks(Storm())
        self.assertEqual(sorted(tracks), ['AVNO', 'CMC', 'OFCL'])
        self.assertEqual(sorted(cycles), ['AVNO', 'CMC', 'OFCL'])

    def test_spaghetti_fetch_failure_returns_empty(self):
        class Broken:
            def get_operational_forecasts(self):
                raise RuntimeError('offline')
        self.assertEqual(_extract_spaghetti_tracks(Broken()), ({}, {}))

    def test_dashboard_shows_model_cycle_and_cone_advisory_time(self):
        from unittest import mock
        basin_data = TestHTMLGeneration()._make_basin_data()
        arthur = basin_data[0]['current']['storm_details']['Arthur']
        arthur.update({
            'is_active': True,
            'spaghetti': {'OFCL': [{'lat': 26.0, 'lon': -91.0}]},
            'spaghetti_cycles': {'OFCL': '2026-09-27T00:00:00Z'},
            'cone_issued': '2026-09-27T03:00:00Z',
        })
        with mock.patch('ace_data.fetch_active_storm_cones', return_value={'Arthur': 'cones/al012026.png'}), \
             mock.patch('ace_data.fetch_nhc_disturbances', return_value=[]):
            html = generate_dashboard_html(basin_data)
        self.assertIn('"spaghetti_cycles": {"OFCL": "00Z Sep 27"}', html)
        self.assertIn('Latest run of each model (UTC)', html)
        self.assertIn('alt="NHC forecast cone for Arthur, advisory issued Sep 27, 2026 03:00 UTC"', html)
        self.assertIn('advisory issued <time datetime="2026-09-27T03:00:00Z">', html)

    def test_cone_without_issue_time_keeps_plain_credit(self):
        from unittest import mock
        basin_data = TestHTMLGeneration()._make_basin_data()
        basin_data[0]['current']['storm_details']['Arthur']['is_active'] = True
        with mock.patch('ace_data.fetch_active_storm_cones', return_value={'Arthur': 'cones/al012026.png'}), \
             mock.patch('ace_data.fetch_nhc_disturbances', return_value=[]):
            html = generate_dashboard_html(basin_data)
        self.assertIn('alt="NHC forecast cone for Arthur"', html)
        self.assertNotIn('advisory issued', html)


class TestBuildSeasonPayload(unittest.TestCase):
    """build_season_payload() is the single source for pages, feeds and the API:
    plain data, no HTML, and the only place the render-time fetches happen."""

    def _payload(self, mutate=None, cones=None, disturbances=()):
        basin_data = TestHTMLGeneration()._make_basin_data()[0]
        basin_data['current']['storms']['Bertha'] = 3.0
        basin_data['current']['storm_details']['Bertha'] = {
            'ace': 3.0, 'max_wind': 70, 'is_active': True, 'start_date': '7/2',
            'spaghetti': {'GFS': [{'lat': 1, 'lon': 2}]},
            'spaghetti_cycles': {'GFS': '2026-07-02T06:00:00Z', 'GONE': 'x'},
        }
        basin_data['current']['total'] = 3.41
        if mutate:
            mutate(basin_data)
        with mock.patch('ace_data.fetch_active_storm_cones', return_value=cones or {}) as fc, \
             mock.patch('ace_data.fetch_nhc_disturbances', return_value=list(disturbances)):
            payload = ace_data.build_season_payload(basin_data)
        return payload, fc

    def test_storms_sorted_by_ace_with_derived_fields(self):
        p, _ = self._payload()
        self.assertEqual([s['name'] for s in p['storms']], ['Bertha', 'Arthur'])
        bertha = p['storms'][0]
        self.assertEqual(bertha['slug'], 'bertha')
        self.assertEqual(bertha['category'], get_category(70))
        self.assertFalse(bertha['is_major'])
        self.assertAlmostEqual(bertha['pct_of_season'], 3.0 / 3.41 * 100)
        self.assertEqual((p['named_storms'], p['hurricanes'], p['major_hurricanes']), (2, 1, 0))

    def test_storm_without_details_gets_safe_defaults(self):
        def drop(bd):
            del bd['current']['storm_details']['Arthur']
        p, _ = self._payload(drop)
        arthur = next(s for s in p['storms'] if s['name'] == 'Arthur')
        self.assertEqual((arthur['max_wind'], arthur['category'], arthur['start_date']), (0, '—', '—'))
        self.assertEqual(arthur['track_points'], [])

    def test_cone_fetch_runs_before_storms_are_read(self):
        """The fetch corrects is_active in place; the payload must see the fix."""
        basin_data = TestHTMLGeneration()._make_basin_data()[0]
        basin_data['current']['storm_details']['Arthur'].update(
            {'is_active': True, 'spaghetti': {'GFS': [{'lat': 1, 'lon': 2}]}})

        def fake_fetch(basin_key, details):
            details['Arthur']['is_active'] = False
            return {'Arthur': 'cones/al012026.png'}
        with mock.patch('ace_data.fetch_active_storm_cones', side_effect=fake_fetch), \
             mock.patch('ace_data.fetch_nhc_disturbances', return_value=[]):
            p = ace_data.build_season_payload(basin_data)
        arthur = p['storms'][0]
        self.assertFalse(arthur['is_active'])
        self.assertEqual(arthur['spaghetti'], {})
        self.assertIsNone(arthur['cone_image'])

    def test_active_storm_keeps_cone_and_only_model_runs_with_tracks(self):
        p, _ = self._payload(cones={'Bertha': 'cones/x.png'})
        bertha = p['storms'][0]
        self.assertEqual(bertha['cone_image'], 'cones/x.png')
        self.assertEqual(bertha['spaghetti_cycles'], {'GFS': '2026-07-02T06:00:00Z'})

    def test_season_summary_fields(self):
        p, _ = self._payload(disturbances=[{'area': 'a'}])
        self.assertEqual((p['basin_key'], p['basin_name'], p['year']), ('atlantic', 'Atlantic', 2026))
        self.assertEqual(p['ace_total'], 3.41)
        self.assertEqual(p['classification'], ace_data.get_noaa_classification(3.41, 'atlantic'))
        self.assertEqual(p['rank'], 4)
        self.assertEqual(p['total_seasons'], 4)
        self.assertEqual(p['disturbances'], [{'area': 'a'}])
        self.assertFalse(p['preseason'])
        self.assertFalse(p['is_backup'])

    def test_preseason_has_no_storms_or_rank(self):
        def empty(bd):
            bd['current'].update({'storms': {}, 'storm_details': {}, 'total': 0.0,
                                  'year': ace_data._utc_now().year})
        p, _ = self._payload(empty)
        self.assertTrue(p['preseason'])
        self.assertEqual(p['storms'], [])
        self.assertIsNone(p['rank'])

    def test_payload_is_json_serializable_with_no_html(self):
        p, _ = self._payload(cones={'Bertha': 'cones/x.png'})
        text = json.dumps(p)
        self.assertNotIn('<div', text)
        self.assertNotIn('<span', text)


class TestFeeds(unittest.TestCase):
    """ace_feeds: the JSON API is a public contract and the RSS must be valid XML."""

    NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

    def _payloads(self):
        basin_data = TestHTMLGeneration()._make_basin_data()[0]
        basin_data['current']['storm_details']['Arthur'].update(
            {'landfall_estimated': True, 'start_date': '6/15'})
        with mock.patch('ace_data.fetch_active_storm_cones', return_value={}), \
             mock.patch('ace_data.fetch_nhc_disturbances', return_value=[]):
            return [ace_data.build_season_payload(basin_data)]

    def test_api_v1_shape_is_stable(self):
        api = ace_feeds.build_api_v1(self._payloads(), self.NOW)
        self.assertEqual(api['version'], 1)
        self.assertEqual(api['generated_at'], '2026-09-20T12:00:00Z')
        self.assertEqual(set(api['basins']), {'atlantic'})
        atl = api['basins']['atlantic']
        self.assertEqual(set(atl), {
            'name', 'year', 'preseason', 'is_backup_data', 'data_as_of', 'ace_total', 'normal_ace',
            'pct_of_normal', 'classification', 'named_storms', 'hurricanes', 'major_hurricanes',
            'rank', 'seasons_ranked', 'storms', 'yearly_ace'})
        storm = atl['storms'][0]
        self.assertEqual(set(storm), {
            'name', 'slug', 'ace', 'pct_of_season', 'max_wind_kt', 'category', 'is_major',
            'is_active', 'start_date', 'landfalls', 'landfall_estimated', 'track'})
        self.assertEqual(storm['landfalls'], [{'location': 'Texas', 'category': 'TS'}])
        self.assertEqual(set(storm['track'][0]), {'lat', 'lon', 'wind_kt', 'status', 'time'})
        self.assertEqual(atl['yearly_ace']['2005'], 245.0)

    def test_api_v1_json_round_trips(self):
        text = ace_feeds.api_v1_json(self._payloads(), self.NOW)
        self.assertEqual(json.loads(text)['basins']['atlantic']['storms'][0]['name'], 'Arthur')

    def test_rss_is_valid_xml_with_one_item_per_storm(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(ace_feeds.build_rss(self._payloads(), self.NOW))
        self.assertEqual(root.tag, 'rss')
        items = root.findall('./channel/item')
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.findtext('title'), 'Arthur (Atlantic 2026)')
        self.assertEqual(item.findtext('guid'), 'aceofcanes:atlantic:2026:arthur')
        self.assertEqual(item.findtext('link'), 'https://aceofcanes.com/#storm-row-arthur')
        self.assertEqual(item.findtext('pubDate'), 'Mon, 15 Jun 2026 00:00:00 +0000')
        self.assertIn('landfall (estimated): Texas (TS)', item.findtext('description'))

    def test_rss_escapes_markup_in_storm_names(self):
        import xml.etree.ElementTree as ET
        payloads = self._payloads()
        payloads[0]['storms'][0]['name'] = 'A&B <x>'
        payloads[0]['storms'][0]['slug'] = 'a&b-<x>'
        root = ET.fromstring(ace_feeds.build_rss(payloads, self.NOW))
        self.assertEqual(root.findtext('./channel/item/title'), 'A&B <x> (Atlantic 2026)')
        self.assertNotIn('<x>', root.findtext('./channel/item/link'))

    def test_rss_preseason_is_valid_with_no_items(self):
        import xml.etree.ElementTree as ET
        payloads = self._payloads()
        payloads[0]['storms'] = []
        root = ET.fromstring(ace_feeds.build_rss(payloads, self.NOW))
        self.assertEqual(root.findall('./channel/item'), [])

    def test_rss_item_limit_and_newest_first(self):
        import xml.etree.ElementTree as ET
        payloads = self._payloads()
        base = payloads[0]['storms'][0]
        payloads[0]['storms'] = [dict(base, name=f'S{i}', slug=f's{i}', start_date=f'{1 + i // 28}/{1 + i % 28}')
                                 for i in range(60)]
        items = ET.fromstring(ace_feeds.build_rss(payloads, self.NOW)).findall('./channel/item')
        self.assertEqual(len(items), ace_feeds.FEED_ITEM_LIMIT)
        self.assertEqual(items[0].findtext('title'), 'S59 (Atlantic 2026)')

    def test_dashboard_advertises_feed(self):
        html = generate_dashboard_html(TestHTMLGeneration()._make_basin_data())
        self.assertIn('<link rel="alternate" type="application/rss+xml"', html)


class TestShareCard(unittest.TestCase):
    """Live season share card: a bad image must never break the publish."""

    NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

    def _payloads(self):
        basin_data = TestHTMLGeneration()._make_basin_data()[0]
        with mock.patch('ace_data.fetch_active_storm_cones', return_value={}), \
             mock.patch('ace_data.fetch_nhc_disturbances', return_value=[]):
            return [ace_data.build_season_payload(basin_data)]

    def test_renders_1200x630_png(self):
        from PIL import Image
        png = ace_cards.render_share_card(self._payloads(), self.NOW)
        img = Image.open(io.BytesIO(png))
        self.assertEqual((img.format, img.size), ('PNG', (1200, 630)))

    def test_preseason_and_empty_inputs_still_render(self):
        payloads = self._payloads()
        payloads[0].update({'preseason': True, 'storms': [], 'named_storms': 0, 'rank': None,
                            'total_seasons': None, 'ace_total': 0.0})
        self.assertTrue(ace_cards.render_share_card(payloads, self.NOW).startswith(b'\x89PNG'))
        self.assertTrue(ace_cards.render_share_card([], self.NOW).startswith(b'\x89PNG'))

    def test_filename_changes_only_when_displayed_numbers_change(self):
        payloads = self._payloads()
        name = ace_cards.share_card_name(payloads, self.NOW)
        self.assertRegex(name, r'^og/season-[0-9a-f]{10}\.png$')
        later_same_day = self.NOW.replace(hour=18)
        self.assertEqual(ace_cards.share_card_name(payloads, later_same_day), name)
        payloads[0]['ace_total'] += 0.1
        self.assertNotEqual(ace_cards.share_card_name(payloads, self.NOW), name)
        self.assertNotEqual(ace_cards.share_card_name(self._payloads(), self.NOW + timedelta(days=1)), name)

    def test_alt_text_states_the_numbers(self):
        alt = ace_cards.share_card_alt(self._payloads())
        self.assertIn('Atlantic 0.4 ACE', alt)

    def test_write_share_card_saves_file_and_returns_site_path(self):
        import tempfile
        from ace_tracker import write_share_card
        with tempfile.TemporaryDirectory() as tmp:
            rel, alt = write_share_card(self._payloads(), tmp, self.NOW)
            self.assertTrue(os.path.getsize(os.path.join(tmp, rel)) > 1000)
            self.assertIn('ACE', alt)

    def test_write_share_card_failure_returns_none_instead_of_raising(self):
        import tempfile
        from ace_tracker import write_share_card
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch('ace_cards.render_share_card', side_effect=OSError('no font')):
            self.assertEqual(write_share_card(self._payloads(), tmp, self.NOW), (None, None))

    def test_dashboard_uses_the_card_in_og_and_twitter_tags(self):
        from ace_html import render_dashboard_html
        html = render_dashboard_html(self._payloads(), 'og/season-abc.png', 'Alt <text>')
        self.assertEqual(html.count('https://aceofcanes.com/og/season-abc.png'), 2)
        self.assertIn('property="og:image" content="https://aceofcanes.com/og/season-abc.png"', html)
        self.assertIn('name="twitter:image" content="https://aceofcanes.com/og/season-abc.png"', html)
        self.assertIn('og:image:alt" content="Alt &lt;text&gt;"', html)
        self.assertNotIn('ace_preview.png', html)

    def test_pages_fall_back_to_the_static_preview(self):
        from ace_html import render_dashboard_html
        self.assertEqual(render_dashboard_html(self._payloads()).count('https://aceofcanes.com/ace_preview.png'), 2)
        history = generate_history_html(TestHTMLGeneration()._make_basin_data())
        self.assertEqual(history.count('https://aceofcanes.com/ace_preview.png'), 2)


class TestCanonicalHomeLinks(unittest.TestCase):
    """Links back to the dashboard use its canonical URL "/" so search
    engines do not see "/" and "/index.html" as two pages."""

    def test_pages_link_home_to_root(self):
        basin_data = TestHTMLGeneration()._make_basin_data()
        for gen in (generate_history_html, generate_records_html, generate_about_html):
            with self.subTest(page=gen.__name__):
                html = gen(basin_data)
                self.assertIn('<a href="/">← Current Season</a>', html)
                self.assertNotIn('index.html', html)

    def test_what_is_ace_dashboard_link_keeps_basin_anchor(self):
        html = generate_about_html(TestHTMLGeneration()._make_basin_data())
        self.assertIn('<a href="/#atlantic">See the live dashboard</a>', html)


class TestVendoredLibraries(unittest.TestCase):
    """Leaflet and Chart.js are served from our own domain (data/vendor/,
    deployed with the rest of data/) instead of a single third-party CDN."""

    def _dashboard(self):
        return generate_dashboard_html(TestHTMLGeneration()._make_basin_data())

    def test_no_third_party_cdn_for_libraries(self):
        self.assertNotIn('unpkg.com', self._dashboard())

    def test_vendored_files_match_their_integrity_hashes(self):
        import base64
        import hashlib
        import os
        import re
        html = self._dashboard()
        refs = re.findall(r'(?:src|href)="(vendor/[^"]+)" integrity="sha384-([^"]+)"', html)
        self.assertEqual(sorted(r[0] for r in refs), [
            'vendor/chart.js-4.5.1/chart.umd.min.js',
            'vendor/leaflet-1.9.4/leaflet.css',
            'vendor/leaflet-1.9.4/leaflet.js',
        ])
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        for path, digest in refs:
            with self.subTest(file=path):
                with open(os.path.join(data_dir, path), 'rb') as f:
                    actual = base64.b64encode(hashlib.sha384(f.read()).digest()).decode()
                self.assertEqual(actual, digest)

    def test_leaflet_assets_and_licenses_shipped(self):
        import os
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'vendor')
        for rel in ('leaflet-1.9.4/images/layers.png', 'leaflet-1.9.4/images/marker-icon.png',
                    'leaflet-1.9.4/LICENSE', 'chart.js-4.5.1/LICENSE.md'):
            with self.subTest(file=rel):
                self.assertTrue(os.path.isfile(os.path.join(base, rel)))

    def test_stylesheet_does_not_block_render(self):
        html = self._dashboard()
        self.assertIn('href="vendor/leaflet-1.9.4/leaflet.css"', html)
        self.assertIn('media="print" onload="this.media=\'all\'"', html)
        self.assertIn('<noscript><link rel="stylesheet" href="vendor/leaflet-1.9.4/leaflet.css"></noscript>', html)

    def test_fallback_text_when_a_library_fails_to_load(self):
        html = self._dashboard()
        self.assertIn("if(typeof L==='undefined')", html)
        self.assertIn('Map unavailable right now.', html)
        self.assertIn('Chart unavailable right now.', html)


class TestFirstHurricaneDates(unittest.TestCase):
    """hurricane_date / major_date come from the first HU point at 64 / 96 kt."""

    class _Storm:
        def __init__(self, rows):
            self.time = [r[0] for r in rows]
            self.type = [r[1] for r in rows]
            self.vmax = [r[2] for r in rows]

    def test_thresholds(self):
        t = [datetime(2026, 9, 1, h) for h in (0, 6, 12, 18)] + [datetime(2026, 9, 2, 0)]
        storm = self._Storm([(t[0], 'TS', 55), (t[1], 'HU', 60), (t[2], 'HU', 64),
                             (t[3], 'HU', 95), (t[4], 'HU', 96)])
        self.assertEqual(_first_track_time(storm, {'HU'}, 64), t[2])  # HU at 60 kt doesn't count
        self.assertEqual(_first_track_time(storm, {'HU'}, 96), t[4])

    def test_extratropical_winds_do_not_count(self):
        t = [datetime(2026, 10, 1, h) for h in (0, 6)]
        storm = self._Storm([(t[0], 'TS', 60), (t[1], 'EX', 100)])
        self.assertIsNone(_first_track_time(storm, {'HU'}, 64))

    def test_unreadable_track_returns_none(self):
        class Broken:
            @property
            def time(self):
                raise RuntimeError('no track')
        self.assertIsNone(_first_track_time(Broken(), {'HU'}, 64))


class TestTcrFetchFailure(unittest.TestCase):
    """The NHC report index failing to download degrades to season links."""

    def test_network_error_returns_empty(self):
        from unittest import mock
        import ace_data
        saved = ace_data._tcr_rows_cache
        ace_data._tcr_rows_cache = None
        try:
            with mock.patch('urllib.request.urlopen', side_effect=OSError('offline')):
                self.assertEqual(fetch_tcr_reports([{'id': 'AL012005', 'name': 'Arlene', 'year': 2005}],
                                                   'atlantic'), {})
            self.assertIsNone(ace_data._tcr_rows_cache)
        finally:
            ace_data._tcr_rows_cache = saved
class TestHurdatSanitizer(unittest.TestCase):
    """Malformed HURDAT2 rows are dropped and attributed to their storm, so
    the log says whether they matter for this site (1991+)."""

    # The two rows NOAA's Sept 2026 revision shipped malformed.
    RAW = "\n".join([
        "AL211969,            UNNAMED,      3,",
        "19690928, 1800,  , EX, 62.0N,   10.0W,  70, -999",
        "19690929, 0600,  , EX, 63.3N    7.5E,  70, -999",
        "19690929, 1200,  , EX, 64.0N,    5.0E,  65, -999",
        "AL231975,            UNNAMED,      2,",
        "19751207, 0000,  , EX, 38.83,  51.0W,  50, -999",
        "19751207, 0600,  , EX, 39.5N,  50.0W,  45, -999",
    ])

    def test_drops_bad_rows_and_names_their_storms(self):
        kept, dropped = _drop_malformed_hurdat_rows(self.RAW)
        self.assertEqual(dropped, ['AL211969', 'AL231975'])
        self.assertEqual(len(kept), 5)
        self.assertNotIn('63.3N    7.5E', '\n'.join(kept))
        self.assertIn('AL231975,', '\n'.join(kept))

    def test_clean_file_keeps_everything(self):
        clean = "\n".join(l for l in self.RAW.splitlines() if '7.5E,' not in l and '38.83,' not in l)
        kept, dropped = _drop_malformed_hurdat_rows(clean)
        self.assertEqual(dropped, [])
        self.assertEqual(len(kept), 5)


# ===============================================================================
# FIXTURE TESTS FOR NETWORK-DEPENDENT FETCHERS (#112)
# Tropycal objects are faked in-process; NHC responses are files in fixtures/.
# ===============================================================================


FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def _fixture_bytes(name):
    with open(os.path.join(FIXTURES, name), 'rb') as f:
        return f.read()


class _Resp(io.BytesIO):
    """Stands in for the context manager urllib.request.urlopen returns."""
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeStorm:
    """Minimal Tropycal Storm: parallel track arrays plus the attributes
    ace_data reads. `points` are (time, type, vmax, lat, lon) tuples."""

    def __init__(self, storm_id, name, points, special=None, forecasts=None):
        self.id = storm_id
        self.name = name
        self.year = points[0][0].year
        self.time = [p[0] for p in points]
        self.type = [p[1] for p in points]
        self.vmax = [p[2] for p in points]
        self.lat = [p[3] for p in points]
        self.lon = [p[4] for p in points]
        self.special = special or [''] * len(points)
        self.ace = 0.0
        self._forecasts = forecasts

    def get_operational_forecasts(self):
        if self._forecasts is None:
            raise RuntimeError('no forecasts')
        return self._forecasts


class FakeDataset:
    """Minimal Tropycal TrackDataset. get_season raises for a year with no
    storms, like Tropycal does; get_storm raises for an id in `broken`."""

    def __init__(self, storms, broken=()):
        self._storms = {s.id: s for s in storms}
        self._broken = set(broken)
        self._seasons = {}
        for s in storms:
            self._seasons.setdefault(s.year, []).append(s.id)
        for sid, year in self._broken:
            self._seasons.setdefault(year, []).append(sid)

    def get_season(self, year):
        if year not in self._seasons:
            raise ValueError(f'no {year} season')
        return mock.Mock(dict={sid: {} for sid in self._seasons[year]})

    def get_storm(self, storm_id):
        if storm_id not in self._storms:
            raise RuntimeError(f'corrupt storm {storm_id}')
        return self._storms[storm_id]


class TestParseHurdat2Fixtures(unittest.TestCase):
    """parse_hurdat2 turns Tropycal storms into the historical storm records
    the whole site is built from."""

    ANA_1991 = [
        (datetime(1991, 6, 29, 18), 'TD', 25, 31.5, -78.5),
        (datetime(1991, 6, 30, 0), 'TS', 35, 32.0, -77.8),
        (datetime(1991, 6, 30, 3), 'TS', 45, 32.3, -77.3),   # off-synoptic: no ACE
        (datetime(1991, 6, 30, 6), 'TS', 40, 32.6, -76.9),
        (datetime(1991, 6, 30, 12), 'EX', 70, 33.4, -75.6),  # extratropical: no ACE, no peak
    ]
    FAY_2026 = [
        (datetime(2026, 9, 1, 0), 'TS', 50, 25.0, -60.0),
        (datetime(2026, 9, 1, 6), 'HU', 90, 26.0, -61.0),
    ]

    def _run(self, dataset, cache):
        with mock.patch.object(ace_data, '_utc_now', return_value=datetime(2026, 10, 3, 12)), \
             mock.patch.object(ace_data, '_load_landfall_cache', return_value=cache), \
             mock.patch.object(ace_data, '_save_landfall_cache') as save, \
             mock.patch.object(ace_data, 'get_landfall_locations',
                               return_value=[('Bermuda', 'Cat 1')]) as geo:
            storms = ace_data.parse_hurdat2('atlantic', dataset=dataset)
        return storms, save, geo

    def test_builds_records_from_tropical_synoptic_points(self):
        dataset = FakeDataset([FakeStorm('AL011991', 'ANA', self.ANA_1991),
                               FakeStorm('AL062026', 'FAY', self.FAY_2026)])
        storms, _, _ = self._run(dataset, {'AL011991': [('North Carolina', 'TS')]})
        by_id = {s['id']: s for s in storms}
        ana = by_id['AL011991']
        self.assertEqual(ana['name'], 'Ana')
        self.assertEqual(ana['wind_readings'], [35, 40])
        self.assertAlmostEqual(ana['ace'], 0.2825)
        self.assertEqual(ana['max_wind'], 45)
        self.assertEqual(ana['formation_date'], datetime(1991, 6, 30, 0))
        self.assertIsNone(ana['hurricane_date'])
        fay = by_id['AL062026']
        self.assertAlmostEqual(fay['ace'], 1.06)
        self.assertEqual(fay['category'], 'Cat 2')
        self.assertEqual(fay['hurricane_date'], datetime(2026, 9, 1, 6))

    def test_landfall_cache_keys_by_id_for_past_and_by_track_for_current(self):
        dataset = FakeDataset([FakeStorm('AL011991', 'ANA', self.ANA_1991),
                               FakeStorm('AL062026', 'FAY', self.FAY_2026)])
        cache = {'AL011991': [('North Carolina', 'TS')],
                 'cur:AL062026:2026083100': [('Old', 'TS')]}
        storms, save, geo = self._run(dataset, cache)
        by_id = {s['id']: s for s in storms}
        self.assertEqual(by_id['AL011991']['landfall'], [('North Carolina', 'TS')])
        self.assertEqual(by_id['AL062026']['landfall'], [('Bermuda', 'Cat 1')])
        geo.assert_called_once()  # only the uncached current-season storm
        saved = save.call_args[0][0]
        self.assertIn('cur:AL062026:2026090106', saved)
        self.assertNotIn('cur:AL062026:2026083100', saved)

    def test_cache_fully_hit_skips_save(self):
        dataset = FakeDataset([FakeStorm('AL011991', 'ANA', self.ANA_1991)])
        _, save, geo = self._run(dataset, {'AL011991': []})
        geo.assert_not_called()
        save.assert_not_called()

    def test_one_corrupt_storm_does_not_drop_the_season(self):
        dataset = FakeDataset([FakeStorm('AL011991', 'ANA', self.ANA_1991)],
                              broken=[('AL021991', 1991)])
        storms, _, _ = self._run(dataset, {'AL011991': []})
        self.assertEqual([s['id'] for s in storms], ['AL011991'])

    def test_dataset_build_failure_returns_none_for_backup(self):
        with mock.patch.object(ace_data, '_build_track_dataset', side_effect=RuntimeError('down')):
            self.assertIsNone(ace_data.parse_hurdat2('atlantic'))


class TestGetCurrentSeasonFixtures(unittest.TestCase):
    """get_current_season builds the dashboard's live storm table."""

    def setUp(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
        self.base = now - timedelta(hours=now.hour % 6)
        b = self.base
        self.rachel = FakeStorm('EP182026', 'RACHEL', [
            (b - timedelta(hours=12), 'TS', 45, 17.0, -108.0),
            (b - timedelta(hours=6), 'HU', 70, 18.0, -110.0),
            (b, 'HU', 75, 19.8, -112.5),
        ])
        self.bertha = FakeStorm('EP022026', 'BERTHA', [
            (datetime(2026, 7, 1, 0), 'TS', 40, 15.0, -100.0),
            (datetime(2026, 7, 1, 3), 'TS', 42, 15.2, -100.4),
            (datetime(2026, 7, 1, 6), 'TS', 45, 15.5, -101.0),
        ])
        self.one = FakeStorm('EP012026', 'ONE', [(datetime(2026, 6, 1, 0), 'TD', 30, 12.0, -95.0)])
        self.unnamed = FakeStorm('EP902026', None, [(datetime(2026, 6, 2, 0), 'TS', 40, 12.0, -95.0)])
        for s in (self.rachel, self.bertha, self.one, self.unnamed):
            s.year = 2026

    def _run(self, dataset, today=datetime(2026, 10, 3, 12), landfalls=None):
        landfalls = landfalls or {}
        with mock.patch.object(ace_data, '_utc_now', return_value=today), \
             mock.patch.object(ace_data, '_load_landfall_cache', return_value={}), \
             mock.patch.object(ace_data, '_save_landfall_cache') as save, \
             mock.patch.object(ace_data, 'get_landfall_locations',
                               side_effect=lambda s: landfalls.get(s.id, [])), \
             mock.patch.object(ace_data, '_detect_landfall_from_track',
                               return_value=[('Baja California Sur, Mexico', 'Cat 1')]) as detect, \
             mock.patch.object(ace_data, '_extract_spaghetti_tracks',
                               return_value=({'OFCL': [{'lat': 20.0, 'lon': -113.0}]},
                                             {'OFCL': '2026-10-03T18:00:00Z'})) as spag:
            result = ace_data.get_current_season('pacific', dataset=dataset)
        return result, save, detect, spag

    def test_named_storms_with_ace_track_and_active_flag(self):
        dataset = FakeDataset([self.rachel, self.bertha, self.one, self.unnamed])
        result, _, _, spag = self._run(dataset, landfalls={'EP022026': [('Guerrero, Mexico', 'TS')]})
        self.assertEqual(result['year'], 2026)
        self.assertEqual(set(result['storms']), {'Rachel', 'Bertha'})
        self.assertAlmostEqual(result['storms']['Rachel'], 1.255)
        self.assertAlmostEqual(result['total'], 1.255 + ace_from_winds([40, 45]))
        rachel, bertha = result['storm_details']['Rachel'], result['storm_details']['Bertha']
        self.assertTrue(rachel['is_active'])
        self.assertFalse(bertha['is_active'])
        self.assertEqual(len(bertha['track_points']), 2)  # synoptic times only
        self.assertEqual(bertha['track_points'][0]['time'], '7/1 00Z')
        self.assertEqual(bertha['start_date'], '7/1')
        self.assertEqual(rachel['spaghetti'], {'OFCL': [{'lat': 20.0, 'lon': -113.0}]})
        self.assertEqual(bertha['spaghetti'], {})
        spag.assert_called_once_with(self.rachel)  # model tracks only for active storms
        self.assertEqual(result['data_as_of'], self.base.strftime('%Y-%m-%dT%H:%M:%SZ'))

    def test_landfall_marked_estimated_only_when_geo_fallback_used(self):
        dataset = FakeDataset([self.rachel, self.bertha])
        result, save, detect, _ = self._run(dataset, landfalls={'EP022026': [('Guerrero, Mexico', 'TS')]})
        rachel, bertha = result['storm_details']['Rachel'], result['storm_details']['Bertha']
        self.assertEqual(rachel['landfall'], [('Baja California Sur, Mexico', 'Cat 1')])
        self.assertTrue(rachel['landfall_estimated'])
        self.assertEqual(bertha['landfall'], [('Guerrero, Mexico', 'TS')])
        self.assertFalse(bertha['landfall_estimated'])
        detect.assert_called_once_with(self.rachel)
        geo_key = f"geo:EP182026:{self.base.strftime('%Y%m%d%H')}"
        self.assertIn(geo_key, save.call_args[0][0])

    def test_in_season_with_no_named_storms_returns_empty_season(self):
        result, _, _, _ = self._run(FakeDataset([self.one]))
        self.assertEqual(result, {'year': 2026, 'storms': {}, 'storm_details': {}, 'total': 0.0})

    def test_off_season_with_no_storms_uses_flagged_backup(self):
        result, _, _, _ = self._run(FakeDataset([self.one]), today=datetime(2027, 1, 15))
        self.assertTrue(result['is_backup'])
        self.assertEqual(result['year'], 2027)

    def test_tropycal_failure_in_season_returns_empty_not_backup(self):
        with mock.patch.object(ace_data, '_utc_now', return_value=datetime(2026, 10, 3, 12)), \
             mock.patch.object(ace_data, '_build_track_dataset', side_effect=RuntimeError('down')):
            result = ace_data.get_current_season('atlantic')
        self.assertEqual(result['storms'], {})
        self.assertNotIn('is_backup', result)


class TestHurdatDownloadFixtures(unittest.TestCase):
    """The HURDAT2 download is sanitized before Tropycal parses it."""

    def test_sanitized_file_drops_malformed_rows_and_logs_impact(self):
        with mock.patch('urllib.request.urlopen',
                        return_value=_Resp(_fixture_bytes('hurdat2_snippet.txt'))), \
             self.assertLogs('ace_data', level='WARNING') as logs:
            path = ace_data._sanitize_hurdat_file('https://example.invalid/hurdat2.txt')
        try:
            with open(path) as f:
                text = f.read()
        finally:
            os.remove(path)
        self.assertNotIn('25.0N70.0W', text)
        self.assertIn('19691110, 0600', text)
        self.assertIn('AL011991', text)
        self.assertIn('AL211969 (all before 1991, so no effect', logs.output[0])

    def test_dataset_uses_sanitized_file(self):
        with mock.patch.object(ace_data, 'find_latest_hurdat_files', return_value=('atl.txt', 'pac.txt')), \
             mock.patch.object(ace_data, '_sanitize_hurdat_file', return_value='/tmp/clean.txt') as clean, \
             mock.patch.object(ace_data.tracks, 'TrackDataset') as ds:
            ace_data._build_track_dataset('pacific')
        clean.assert_called_once_with('pac.txt')
        self.assertEqual(ds.call_args.kwargs['pacific_url'], '/tmp/clean.txt')
        self.assertEqual(ds.call_args.kwargs['basin'], 'east_pacific')

    def test_dataset_falls_back_to_tropycal_fetch_when_download_fails(self):
        with mock.patch.object(ace_data, 'find_latest_hurdat_files', side_effect=OSError('offline')), \
             mock.patch.object(ace_data.tracks, 'TrackDataset') as ds, \
             self.assertLogs('ace_data', level='WARNING'):
            ace_data._build_track_dataset('atlantic')
        self.assertNotIn('atlantic_url', ds.call_args.kwargs)
        self.assertTrue(ds.call_args.kwargs['include_btk'])


class TestNhcOutlookFixtures(unittest.TestCase):
    """NHC Tropical Weather Outlook parsing, from saved TWO feeds."""

    def _parse(self, fixture, basin):
        with mock.patch('urllib.request.urlopen', return_value=_Resp(_fixture_bytes(fixture))) as op:
            result = ace_data.fetch_nhc_disturbances(basin)
        return result, op.call_args[0][0].full_url

    def test_active_systems_paragraph_is_not_a_disturbance(self):
        # Real EP outlook, Oct 3 2026: advisories on Nolo and Rachel, plus one
        # unnumbered disturbance. The live site labelled it "Active Systems".
        result, url = self._parse('nhc_two_ep_active_systems.xml', 'pacific')
        self.assertTrue(url.endswith('TWOEP.xml'))
        self.assertEqual(len(result), 1)
        d = result[0]
        self.assertEqual(d['area'], 'South of Southern Mexico')
        self.assertTrue(d['desc'].startswith('An area of low pressure is forecast'))
        self.assertNotIn('Nolo', d['desc'])
        self.assertEqual((d['level_48h'], d['pct_48h'], d['level_7d'], d['pct_7d']), ('LOW', 0, 'HIGH', 90))
        self.assertEqual(d['issued'], 'Sat, 03 Oct 2026 23:29:09 +0000')
        self.assertIn('basin=epac', d['nhc_url'])

    def test_numbered_outlook_keeps_only_medium_or_high(self):
        result, url = self._parse('nhc_two_at_numbered.xml', 'atlantic')
        self.assertTrue(url.endswith('TWOAT.xml'))
        self.assertEqual([d['area'] for d in result], ['Central Tropical Atlantic (AL95)'])
        self.assertEqual((result[0]['level_48h'], result[0]['pct_48h']), ('MEDIUM', 60))
        self.assertTrue(result[0]['desc'].startswith('Showers and thunderstorms'))

    def test_low_chance_only_outlook_is_empty(self):
        result, _ = self._parse('nhc_two_at_quiet.xml', 'atlantic')
        self.assertEqual(result, [])

    def test_network_failure_returns_empty(self):
        with mock.patch('urllib.request.urlopen', side_effect=OSError('offline')), \
             self.assertLogs('ace_data', level='WARNING'):
            self.assertEqual(ace_data.fetch_nhc_disturbances('atlantic'), [])

    def test_unknown_basin_makes_no_request(self):
        with mock.patch('urllib.request.urlopen') as op:
            self.assertEqual(ace_data.fetch_nhc_disturbances('west_pacific'), [])
        op.assert_not_called()


class TestForecastConeFixtures(unittest.TestCase):
    """Cone downloads and the NHC active-list cross-check, from a saved
    CurrentStorms.json (Oct 3 2026: Rachel EP3, Nolo CP2)."""

    def _run(self, basin, details, storms_json=None, image=b'PNG'):
        storms_json = storms_json or _fixture_bytes('nhc_current_storms.json')
        responses = [_Resp(storms_json)]

        def urlopen(req, timeout=None):
            if responses:
                return responses.pop(0)
            if isinstance(image, Exception):
                raise image
            return _Resp(image)

        with mock.patch('urllib.request.urlopen', side_effect=urlopen) as op, \
             mock.patch.object(ace_data.os, 'makedirs'), \
             mock.patch('ace_data.open', mock.mock_open(), create=True) as written:
            images = ace_data.fetch_active_storm_cones(basin, details)
        urls = [c[0][0].full_url for c in op.call_args_list]
        return images, urls, written

    def test_downloads_cone_and_clears_storms_nhc_no_longer_lists(self):
        details = {'Rachel': {'is_active': True}, 'Priscilla': {'is_active': True},
                   'Bertha': {'is_active': False}}
        images, urls, written = self._run('pacific', details)
        self.assertEqual(images, {'Rachel': 'cones/ep182026.png'})
        self.assertEqual(urls[1], 'https://www.nhc.noaa.gov/storm_graphics/EP18/refresh/'
                                  'EP182026_5day_cone+png/032053_5day_cone.png')
        self.assertEqual(details['Rachel']['cone_issued'], '2026-10-03T20:53:08Z')
        self.assertTrue(details['Rachel']['is_active'])
        self.assertFalse(details['Priscilla']['is_active'])
        written().write.assert_called_once_with(b'PNG')

    def test_atlantic_cone_path_uses_at_prefix(self):
        storms_json = json.dumps({'activeStorms': [{
            'id': 'al062026', 'binNumber': 'AT1', 'name': 'Fay',
            'forecastGraphics': {'fileUpdateTime': '2026-09-02T08:51:00.000Z'}}]}).encode()
        images, urls, _ = self._run('atlantic', {'Fay': {'is_active': True}}, storms_json)
        self.assertEqual(images, {'Fay': 'cones/al062026.png'})
        self.assertEqual(urls[1], 'https://www.nhc.noaa.gov/storm_graphics/AT06/refresh/'
                                  'AL062026_5day_cone+png/020851_5day_cone.png')

    def test_other_basins_storms_do_not_count(self):
        details = {'Rachel': {'is_active': True}}
        images, urls, _ = self._run('atlantic', details)
        self.assertEqual(images, {})
        self.assertFalse(details['Rachel']['is_active'])
        self.assertEqual(len(urls), 1)

    def test_no_active_storms_makes_no_request(self):
        with mock.patch('urllib.request.urlopen') as op:
            self.assertEqual(ace_data.fetch_active_storm_cones('pacific', {'Bertha': {'is_active': False}}), {})
        op.assert_not_called()

    def test_feed_failure_leaves_active_flags_alone(self):
        details = {'Rachel': {'is_active': True}}
        with mock.patch('urllib.request.urlopen', side_effect=OSError('offline')), \
             self.assertLogs('ace_data', level='WARNING'):
            self.assertEqual(ace_data.fetch_active_storm_cones('pacific', details), {})
        self.assertTrue(details['Rachel']['is_active'])

    def test_image_failure_keeps_storm_active_without_cone(self):
        details = {'Rachel': {'is_active': True}}
        with self.assertLogs('ace_data', level='WARNING'):
            images, _, _ = self._run('pacific', details, image=OSError('404'))
        self.assertEqual(images, {})
        self.assertTrue(details['Rachel']['is_active'])
        self.assertNotIn('cone_issued', details['Rachel'])


class TestLandfallGeocodingFixtures(unittest.TestCase):
    """Landfall naming and track-crossing detection against fake Natural
    Earth records (boxes), so no shapefile download is needed."""

    @staticmethod
    def _geocoder():
        from shapely.geometry import box

        def rec(geom, attrs):
            r = mock.Mock(geometry=geom, attributes=attrs)
            return (r, geom.bounds)
        states = [rec(box(-87, 25, -80, 31), {'name': 'Florida', 'admin': 'United States of America'}),
                  rec(box(-89, 18, -86.7, 21.6), {'name': 'Quintana Roo', 'admin': 'Mexico'})]
        countries = [rec(box(-85, 19.8, -74, 23.2), {'NAME': 'Cuba'})]
        return states, countries

    def setUp(self):
        patcher = mock.patch.object(ace_data, '_build_landfall_geocoder', side_effect=self._geocoder)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reverse_geocode_prefers_state_then_country(self):
        self.assertEqual(ace_data._reverse_geocode(25.2, -80.5), 'Florida')  # within the coastal buffer
        self.assertEqual(ace_data._reverse_geocode(20.0, -87.5), 'Quintana Roo, Mexico')
        self.assertEqual(ace_data._reverse_geocode(23.5, -79.0), 'Cuba')
        self.assertIsNone(ace_data._reverse_geocode(10.0, -40.0))

    def test_hurdat_l_markers_give_category_at_landfall(self):
        storm = FakeStorm('AL092026', 'IAN', [
            (datetime(2026, 9, 27, 6), 'HU', 110, 22.5, -83.5),
            (datetime(2026, 9, 28, 18), 'HU', 130, 26.7, -82.2),
            (datetime(2026, 9, 29, 0), 'HU', 120, 27.0, -82.0),
        ], special=['L', 'L', ''])
        self.assertEqual(ace_data.get_landfall_locations(storm), [('Cuba', 'Cat 3'), ('Florida', 'Cat 4')])

    def test_track_crossing_water_to_land_is_a_landfall(self):
        storm = FakeStorm('AL102026', 'JULIA', [
            (datetime(2026, 10, 1, 0), 'TS', 50, 22.0, -88.0),    # water
            (datetime(2026, 10, 1, 6), 'HU', 70, 22.0, -80.0),    # Cuba
            (datetime(2026, 10, 1, 12), 'HU', 65, 24.0, -81.0),   # water
            (datetime(2026, 10, 1, 15), 'TS', 55, 26.0, -81.0),   # off-synoptic: ignored
            (datetime(2026, 10, 1, 18), 'TS', 50, 26.0, -81.0),   # Florida
            (datetime(2026, 10, 2, 0), 'TS', 40, 27.0, -81.0),    # still over Florida
        ])
        self.assertEqual(ace_data._detect_landfall_from_track(storm),
                         [('Cuba', 'Cat 1'), ('Florida', 'TS')])

    def test_track_starting_over_land_is_not_a_landfall(self):
        storm = FakeStorm('AL112026', 'KARL', [
            (datetime(2026, 10, 5, 0), 'TD', 30, 28.0, -82.0),
            (datetime(2026, 10, 5, 6), 'TS', 40, 29.0, -82.0),
        ])
        self.assertEqual(ace_data._detect_landfall_from_track(storm), [])


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
