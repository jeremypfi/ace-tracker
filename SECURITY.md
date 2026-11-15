# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest (main branch) | ✅ |

## Security Considerations

This project is a hurricane tracking tool that:
- ✅ Uses **public data** from NOAA (no authentication required)
- ✅ Has **no user authentication** system
- ✅ Contains **no sensitive data**
- ✅ Publishes only **public hurricane data** to GitHub Pages
- ✅ **No API keys or credentials** anywhere in the codebase

## Data Privacy

**What this tool does:**
- Downloads public hurricane data from NOAA via the Tropycal library
- Generates Excel spreadsheets locally in `data/`
- Generates HTML dashboards locally in `data/`
- Publishes the site (HTML pages, share-card PNGs, the JSON API, the storm search index, RSS feed and sitemap) to GitHub Pages at https://aceofcanes.com via GitHub Actions: hourly May–November, every 3 hours December–April

**What this tool does NOT do:**
- ❌ Collect personal information or run a server of its own (the site is static files)
- ❌ Require API keys or credentials
- ❌ Store passwords or tokens
- ❌ Set cookies or use advertising trackers

**What a visitor's browser sends, and to whom:**
- **Cloudflare Web Analytics** (`static.cloudflareinsights.com`): page views and load timing, used for aggregate visitor counts. Cloudflare's analytics sets no cookies.
- **OpenFreeMap** (`tiles.openfreemap.org`): map tiles for the area being viewed.
- **NOAA** (`mapservices.weather.noaa.gov`): NHC advisory layers, only when an active storm's map is opened.
- **Nominatim / OpenStreetMap** (`nominatim.openstreetmap.org`): the place text typed into "Show where you are on the map", only when the visitor searches. Their location itself never leaves the browser.

**What the site keeps in the visitor's browser (`localStorage`, never sent anywhere):**
- `ace-theme` and `ace-wind-unit`: display preferences
- `ace-location`: the visitor's map location, only if they tick "Remember on this device"; "Clear location" or "Forget location" removes it

## Dependencies

This project relies on third-party Python packages (see `requirements.txt`):
- `tropycal` — hurricane data library (HURDAT2 + NHC best track)
- `shapely`, `cartopy` — geographic calculations (via Tropycal)
- `pillow` — share-card images
- `setuptools>=84.1.0,<85` — floor for GHSA-xmj3-9gf7-h52w; cap kept from the old Tropycal `pkg_resources` dependency

Dependency updates are automated via Dependabot (weekly, grouped minor/patch PRs for Python packages and GitHub Actions). CodeQL code scanning runs on every push and pull request and weekly (Python and workflow files); secret scanning and push protection are on.

**Security best practice:** Always install from official sources:
```bash
uv pip install -r requirements.txt
```

## Reporting a Vulnerability

If you discover a security vulnerability in this project:

1. **Do NOT** open a public issue
2. Report it privately: [**Report a vulnerability**](https://github.com/jeremypfi/ace-tracker/security/advisories/new) (repository **Security** tab → **Report a vulnerability**). Only the maintainer can see the report.
3. Provide details about the vulnerability and how to reproduce it
4. Allow time for a fix before public disclosure

**Response time:** Within 7 days

## Safe Usage Guidelines

### ✅ Safe to do:
- Clone and run this code locally
- Share generated spreadsheets (they contain only public hurricane data)
- Modify the code for your own use
- Fork the repository

### ⚠️ Be careful:
- Don't commit personal modifications with API keys/passwords
- Don't store sensitive data in the `data/` folder if sharing
- Review any dependencies you add for security issues

### ❌ Never do:
- Don't add credentials to the code
- Don't commit `.env` files or API keys
- Don't expose local file paths with personal information

## License

This project is licensed under the MIT License - see LICENSE file.
The license provides the software "as is" without warranty.

---

**Last Updated:** November 14, 2026
