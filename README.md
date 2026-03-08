# London Property Market Analysis 2019-2024

A comprehensive data pipeline and visualisation project analysing London's property prices and rental market across 32 boroughs (2019-2024). Built with Python for data processing and Tableau Public for interactive dashboards.

**[View Interactive Dashboard on Tableau Public](https://public.tableau.com/app/profile/jun.chung.wu/viz/LondonPropertyMarketAnalysis2019-2024/LondonPropertyMarketAnalysis2019-2024)**

## Data Sources

| Data | Source | URL |
|------|--------|-----|
| Property Transactions | HM Land Registry – Price Paid Data | https://www.gov.uk/government/collections/price-paid-data |
| Rental Market | ONS – Private Rental Market Summary Statistics | https://www.ons.gov.uk/peoplepopulationandcommunity/housing/datasets/privaterentalmarketsummarystatisticsinengland |

## Key Features

- **Automated Pipeline**: One-command execution downloads, cleans, and analyses 6 years of property data
- **Multi-level Analysis**: Borough-level and Postcode-level granularity
- **Investment Scoring**: Custom hotspot scoring system combining yield, growth, and affordability
- **5 Interactive Dashboards**: Built in Tableau Public for exploration and storytelling

## Project Structure

```
london_property/
├── main.py                    # One-click pipeline runner
├── download_price.py          # Download Land Registry price data
├── download_rent.py           # Download ONS rental data
├── clean_price.py             # Clean price data (via MySQL)
├── clean_rent.py              # Clean rent data
├── analysis.py                # 9-phase analysis pipeline
├── config.ini                 # Configuration (MySQL + paths)
│
├── property_price/            # Raw price CSVs (pp-YYYY.csv)
├── property_price_filtered/   # Cleaned price CSVs
├── property_rent/             # Raw rent Excel files
├── property_rent_filtered/    # Cleaned rent CSVs (borough + postcode)
├── lookup_table/              # Reference tables (borough mapping, coordinates)
├── map/                       # Shapefiles (borough + postcode boundaries)
│
├── tableau_output/            # Analysis output CSVs for Tableau
│   ├── master_borough/        # Core borough metrics (price, rent, yield, growth)
│   ├── hotspot_borough/       # Investment hotspot scores & ranking
│   ├── affordability/         # Rent-vs-buy affordability analysis
│   ├── price_by_type/         # Price by property type (D/S/T/F)
│   ├── rent_by_room/          # Rent by bedroom count
│   ├── postcode_detail/       # Postcode-level rent breakdown
│   ├── postcode_map/          # Postcode-level map data
│   └── lookup/                # Lookup tables
│
├── images_output/             # Data quality charts (PNG)
├── tableau_file/              # Tableau workbook (.twb)
└── 使用指南.md                 # Detailed usage guide (Chinese)
```

## Pipeline Overview

```
Download → Clean → Analyse → Visualise
```

| Phase | Script | Description |
|-------|--------|-------------|
| 1 | `download_price.py` | Download Land Registry CSVs (pp-YYYY.csv) |
| 2 | `download_rent.py` | Download ONS Excel files, auto-convert .xls to .xlsx |
| 3 | `clean_price.py` | Import to MySQL, filter London, remove outliers, export |
| 4 | `clean_rent.py` | Parse Excel sheets, align boroughs, split by borough/postcode |
| 5 | `analysis.py` | 9-phase analysis producing 11 CSVs and 6 quality charts |

The full pipeline can be executed with a single command: `python main.py`

## Dashboards (Tableau Public)

| # | Dashboard | Description |
|---|-----------|-------------|
| 1 | **London Property Overview** | Borough map, price/rent trends, direction comparison, KPIs |
| 2 | **Investment Hotspot Analysis** | Yield vs growth scoring, borough ranking, CAGR comparison |
| 3 | **Affordability Analysis** | Rent-vs-mortgage ratio, price-to-rent trend, yield scatter |
| 4 | **Property Type & Rent Analysis** | Price by type trend, rent by room count trend |
| 5 | **Postcode Rent Analysis** | Postcode-level rent heatmap, room count breakdown |

## Annual Update

When new data is published (price: monthly, rent: annually in Jan-Feb):

```bash
python main.py
```

Or update manually:

```bash
python download_price.py --year 2025
python download_rent.py --search
python download_rent.py --year 2025
python clean_price.py
python clean_rent.py
python analysis.py
```

## Data Disclaimer

ONS official statement on rental data:
> "The sample used to produce these statistics is **not statistical** and may **not be consistent over time**, as such these data **should not be compared across time periods** or between areas."

Rental data is best used for cross-sectional comparisons and approximate yield estimates, not precise trend analysis.

## Author

Kerry Wu
