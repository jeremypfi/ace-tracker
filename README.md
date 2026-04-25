# 🌀 ACE Tracker

**Atlantic & Eastern Pacific Hurricane ACE Tracker**

A Python-based tool that tracks Accumulated Cyclone Energy (ACE) for Atlantic and Eastern Pacific hurricane seasons with comprehensive storm-by-storm historical data from 1991 onward.

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📊 Features

- **Automated Data Collection**: Fetches real-time storm data from climatlas.com and historical data from NOAA HURDAT2
- **Dual Basin Tracking**: Tracks both Atlantic and Eastern Pacific hurricane seasons
- **Excel Spreadsheets**: Generates detailed Excel files with 5 tabs each:
  - Summary (season overview, stats, and similar years)
  - Current Season Storms (individual storm breakdown)
  - Historical Storms (all storms since 1991)
  - Yearly Totals (ranked historical seasons)
  - Discord Update (copy/paste ready for Discord)
- **Mobile-Friendly Dashboard**: Interactive HTML dashboard with stats, rankings, and insights
- **Discord Integration**: Formatted updates ready to copy and paste into Discord
- **Historical Analysis**:
  - Season rankings back to 1991
  - Similar season comparisons
  - NOAA classification (Below Normal, Near Normal, Above Normal, Extremely Active)
  - Storm intensity breakdowns (Tropical Depressions, Tropical Storms, Hurricanes, Major Hurricanes)

---

## 📸 Screenshots

### Dashboard
The mobile-friendly HTML dashboard provides an at-a-glance view of the current hurricane season:

![Dashboard Preview](images/dashboard-preview.png)
*Interactive dashboard with season stats, storm breakdown, and historical rankings*

### Excel Spreadsheet
Comprehensive Excel workbooks with 5 tabs of detailed data:

![Excel Summary Tab](images/excel-summary.png)
*Summary tab showing season overview and key statistics*

![Excel Storms Tab](images/excel-storms.png)
*Current season storms with ACE breakdown and categories*

> **Note:** To add screenshots to this README:
> 1. Run the tracker: `python3 ace_tracker.py`
> 2. Open `data/ACE_Dashboard.html` in your browser and take a screenshot
> 3. Open one of the Excel files and take screenshots of the tabs
> 4. Save images to the `images/` folder with the filenames shown above
> 5. Commit and push the images to GitHub

---

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- Internet connection (for fetching live data)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jeremypfi/ace-tracker.git
   cd ace-tracker
   ```

2. **Install dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

### Usage

Run the tracker:
```bash
python3 ace_tracker.py
```

The script will:
1. Download the latest storm data from climatlas.com
2. Download historical data from NOAA HURDAT2
3. Generate two Excel spreadsheets in the `data/` folder:
   - `ACE_Tracker_Atlantic.xlsx`
   - `ACE_Tracker_Pacific.xlsx`
4. Create an HTML dashboard: `ACE_Dashboard.html`
5. Print a console report with the latest stats

---

## 📁 Project Structure

```
ace-tracker/
├── README.md              # This file
├── ace_tracker.py         # Main Python script
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
└── data/                 # Generated files (not committed)
    ├── ACE_Tracker_Atlantic.xlsx
    ├── ACE_Tracker_Pacific.xlsx
    └── ACE_Dashboard.html
```

---

## 📖 What is ACE?

**Accumulated Cyclone Energy (ACE)** is a metric used by NOAA to measure the total energy of a tropical cyclone season. It's calculated by squaring the maximum sustained wind speed (in knots) every 6 hours when the system is at tropical storm strength or higher, then summing those values.

**Formula:** ACE = Σ(V²max) × 10⁻⁴

ACE provides a better measure of season activity than just counting named storms, since it accounts for both intensity and duration.

---

## 🎯 Understanding the Data

### Spreadsheet Tabs

1. **Summary** - Quick overview with:
   - Total ACE for the season
   - Percentage of "normal" season
   - Historical ranking (since 1991)
   - Similar past seasons
   - Key season statistics

2. **Current Season Storms** - Individual storm details:
   - Storm name, ACE value, percentage contribution
   - Category, max wind speed, duration
   - Major hurricanes highlighted in red

3. **Historical Storms** - Complete storm database:
   - All storms since 1991 with ACE calculations
   - Category, max wind, duration
   - Current year storms highlighted in yellow

4. **Yearly Totals** - Historical season rankings:
   - All seasons ranked by ACE
   - NOAA classification for each year
   - Storm counts (named storms, hurricanes, major hurricanes)

5. **Discord Update** - Formatted text ready to copy/paste into Discord

### NOAA Season Classifications

- **Below Normal**: < 73 ACE
- **Near Normal**: 73-126 ACE (Atlantic) / 73-159 ACE (Pacific)
- **Above Normal**: 126-159 ACE (Atlantic) / 159+ ACE (Pacific)
- **Extremely Active**: 159+ ACE (Atlantic)

---

## 🔧 Configuration

Edit the `CONFIGURATION` section in `ace_tracker.py` to customize:

- **Output folder**: Change where files are saved
- **Start year**: Adjust the historical range
- **Normal ACE values**: Update baseline comparisons
- **Backup data**: Fallback values if network fails

---

## 🐛 Troubleshooting

### "No module named openpyxl"
```bash
pip3 install openpyxl
```

### "Permission denied" error
```bash
chmod +x ace_tracker.py
```

### Script can't download data
- Check your internet connection
- The script will automatically fall back to backup data if downloads fail
- You'll see a message: `✗ Error fetching current season: ... → Using backup data instead`

### Spreadsheet won't open
- Ensure you have Excel, LibreOffice, or OpenOffice installed
- The `.xlsx` format is compatible with all modern spreadsheet applications

---

## 📊 Data Sources

- **[NOAA HURDAT2](https://www.nhc.noaa.gov/data/#hurdat)** - Historical best-track data (1851-present) for storm tracks, wind speeds, and ACE calculations
- **[Climatlas.com](https://climatlas.com/tropical/)** (Dr. Ryan Maue) - Current season real-time storm data and ACE values from ATCF advisories
- **[NOAA CPC](https://www.cpc.ncep.noaa.gov/products/outlooks/background_information.shtml)** - Season classification thresholds and 1991-2020 climatological normals

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

---

## 📝 License

This project is open source and available under the MIT License.

---

## 🙏 Credits

- Built with Claude (Anthropic)
- Data from NOAA National Hurricane Center and Climatlas.com
- Inspired by hurricane tracking communities on Discord

---

## 🌊 2026 Hurricane Season

Good luck tracking the storms! 🌀

---

**Questions or issues?** Open an issue on GitHub or reach out to [@jeremypfi](https://github.com/jeremypfi)
