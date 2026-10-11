"""Save live NHC GIS layers for every active storm as test fixtures.

Run while storms are active: uv run python fixtures/capture_nhc_gis.py
Writes fixtures/nhc_gis/<UTC date>/ with CurrentStorms.json plus one
GeoJSON file per storm bin and layer. Empty layers are kept on purpose:
NHC drops a storm's layers after its final advisory while still listing it
as post-tropical ('PTC'), and the map must handle that.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

SERVICE = ('https://mapservices.weather.noaa.gov/tropical/rest/services/'
           'tropical/NHC_tropical_weather/MapServer')
CURRENT_STORMS = 'https://www.nhc.noaa.gov/CurrentStorms.json'
LAYERS = {
    'Forecast Points': 'forecast_points',
    'Forecast Track': 'forecast_track',
    'Forecast Cone': 'forecast_cone',
    'Watch-Warning': 'watch_warning',
    'Forecast Wind Radii': 'forecast_wind_radii',
}


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'ACETracker/1.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def layer_ids(service_info, bin_number):
    """Map our layer keys to service layer ids by name, e.g. 'AT4 Forecast Cone'.
    Looked up by name rather than offset so a renumbered service fails loudly."""
    by_name = {layer['name']: layer['id'] for layer in service_info['layers']}
    return {key: by_name[f'{bin_number} {name}'] for name, key in LAYERS.items()}


def main():
    storms = get_json(CURRENT_STORMS)
    active = storms.get('activeStorms', [])
    if not active:
        sys.exit('No active storms; nothing to capture.')

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nhc_gis',
                           datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'CurrentStorms.json'), 'w') as f:
        json.dump(storms, f, indent=1)

    service_info = get_json(f'{SERVICE}?f=json')
    for storm in active:
        bin_number = storm['binNumber']
        for key, layer_id in layer_ids(service_info, bin_number).items():
            data = get_json(f'{SERVICE}/{layer_id}/query?where=1%3D1&outFields=*&f=geojson')
            path = os.path.join(out_dir, f'{bin_number}_{key}.geojson')
            with open(path, 'w') as f:
                json.dump(data, f, separators=(',', ':'))
            print(f"{storm['name']:<10} {bin_number} {key:<20} {len(data.get('features', []))} features")


if __name__ == '__main__':
    main()
