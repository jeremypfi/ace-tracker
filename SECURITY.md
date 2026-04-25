# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest (main branch) | ✅ |

## Security Considerations

This project is a hurricane tracking tool that:
- ✅ Uses **public data** from NOAA (no authentication required)
- ✅ Generates **local files** only (no external uploads)
- ✅ Has **no user authentication** system
- ✅ Contains **no sensitive data**
- ✅ Runs **locally** on your machine

## Data Privacy

**What this tool does:**
- Downloads public hurricane data from NOAA
- Generates Excel spreadsheets locally
- Creates HTML dashboards locally
- All files stored in `data/` folder on your computer

**What this tool does NOT do:**
- ❌ Collect personal information
- ❌ Send data to external servers (except downloading NOAA public data)
- ❌ Require API keys or credentials
- ❌ Store passwords or tokens
- ❌ Track user behavior

## Dependencies

This project relies on third-party Python packages:
- `tropycal` - Hurricane data library
- `openpyxl` - Excel file generation
- `matplotlib`, `cartopy`, `shapely` - Mapping/visualization (via Tropycal)

**Security best practice:** Always install from official sources:
```bash
pip3 install -r requirements.txt
```

## Reporting a Vulnerability

If you discover a security vulnerability in this project:

1. **Do NOT** open a public issue
2. Contact the maintainer privately via GitHub
3. Provide details about the vulnerability
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

**Last Updated:** April 24, 2026
