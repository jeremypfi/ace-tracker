"""Check that the live site is still updating (#157). Run by .github/workflows/freshness.yml.

Usage: python freshness_check.py REPORT_PATH [PUBLISH_CONCLUSIONS]
PUBLISH_CONCLUSIONS is a comma list of the latest completed publish runs,
newest first (from `gh run list`). Exit 0 = healthy, 2 = problems written to
REPORT_PATH as Markdown for the alert issue. In Actions it also writes
publish=true|false to GITHUB_OUTPUT so the workflow can start a missed publish (#199).
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

SEASON_JSON = 'https://aceofcanes.com/api/v1/season.json'
CURRENT_STORMS = 'https://www.nhc.noaa.gov/CurrentStorms.json'
BIN_TO_BASIN = {'AT': 'atlantic', 'EP': 'pacific', 'CP': 'pacific'}
# Post-tropical storms linger in CurrentStorms.json after the final advisory,
# and their best track stops; same rule as ace_data.NHC_NOT_ACTIVE_CLASSIFICATIONS.
NOT_ACTIVE = {'PTC'}
# Publish runs hourly in season (May 15-Nov 30) and every 3 h otherwise;
# GitHub can delay scheduled runs, so allow a few missed runs before alerting.
MAX_PUBLISH_AGE_H = {True: 5, False: 10}
# GitHub runs only a fraction of the hourly publish crons (Oct 2026: 4-5 a day,
# gaps up to 8 h), so the hourly freshness check starts a publish itself once
# the site is two runs behind, well before the alert threshold above.
REPUBLISH_AFTER_H = {True: 2, False: 6}
# Best-track data lags real time by up to ~12 h; past this with an active
# storm in the basin, the data feed itself is stuck.
MAX_DATA_AGE_H = 18


def in_season(now):
    return (now.month, now.day) >= (5, 15) and now.month <= 11


def _parse(ts):
    return datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def _hours(now, ts):
    return (now - _parse(ts)).total_seconds() / 3600


def problems(season, now, active_bins, conclusions):
    """season: the live season.json (None if unreachable). active_bins: NHC bin
    numbers like 'AT4' (None if NHC was unreachable, which skips that check)."""
    found = []
    if conclusions[:2] == ['failure', 'failure']:
        found.append('The last two publish runs failed.')
    if season is None:
        return found + [f'Could not fetch {SEASON_JSON}.']

    limit = MAX_PUBLISH_AGE_H[in_season(now)]
    age = _hours(now, season['generated_at'])
    if age > limit:
        found.append(f"Site last published {age:.1f} h ago ({season['generated_at']}); expected within {limit} h.")

    for basin in sorted({BIN_TO_BASIN.get(b[:2]) for b in active_bins or []} - {None}):
        as_of = season['basins'].get(basin, {}).get('data_as_of')
        if as_of and _hours(now, as_of) > MAX_DATA_AGE_H:
            found.append(f'{basin.title()} has an active NHC storm but storm data is from {as_of} '
                         f'({_hours(now, as_of):.0f} h old).')
    return found


def needs_publish(season, now):
    return season is not None and _hours(now, season['generated_at']) > REPUBLISH_AFTER_H[in_season(now)]


def _get_json(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'ACETracker/1.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except (OSError, ValueError):
            if attempt < tries - 1:
                time.sleep(20)
    return None


def main():
    report_path = sys.argv[1]
    conclusions = [c for c in (sys.argv[2] if len(sys.argv) > 2 else '').split(',') if c]
    now = datetime.now(timezone.utc)
    nhc = _get_json(CURRENT_STORMS)
    active = ([s['binNumber'] for s in nhc.get('activeStorms', []) if s.get('classification') not in NOT_ACTIVE]
              if nhc else None)
    season = _get_json(SEASON_JSON)
    found = problems(season, now, active, conclusions)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"publish={'true' if needs_publish(season, now) else 'false'}\n")

    if not found:
        print('Site is fresh.')
        return
    lines = [f'Freshness check at {now:%Y-%m-%d %H:%M} UTC found:', '']
    lines += [f'- {p}' for p in found]
    repo = os.environ.get('GITHUB_REPOSITORY', 'jeremypfi/ace-tracker')
    lines += ['', f'Check the [Publish Dashboard runs](https://github.com/{repo}/actions/workflows/publish.yml). '
              'This issue closes itself when the next check passes.']
    with open(report_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    sys.exit(2)


if __name__ == '__main__':
    main()
