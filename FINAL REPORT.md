# London Property Market Analysis: Final Report
**Date Range: 2019–2024 | 32 London Boroughs**

---

## 1. Project Objective

This project aims to provide a data-driven analysis of London's property market by combining property transaction records and private rental market data. The goal is to help potential investors and renters understand:

- How property prices and rents vary across London boroughs
- Which boroughs offer the best investment potential
- Whether it is more affordable to rent or buy in each area
- How different property types and bedroom counts affect pricing
- How the market differs at postcode-level granularity

---

## 2. Data Sources

| Data | Source | Period | Records |
|------|--------|--------|---------|
| Property Transactions | HM Land Registry – Price Paid Data | 2019–2024 | ~600,000 London transactions |
| Rental Market | ONS – Private Rental Market Summary Statistics | 2019–2024 | Borough & Postcode level |

### Data Limitations

- **Rental data** is based on a non-statistical sample (ONS disclaimer) and should be used for cross-sectional comparison rather than precise trend analysis.
- **Property price data** covers completed transactions only; off-market sales are excluded.
- City of London is excluded due to minimal residential transactions.

---

## 3. Methodology

### 3.1 Data Pipeline

```
Download → Clean → Analyse → Visualise
```

1. **Download**: Automated scripts fetch raw data from Land Registry and ONS
2. **Clean**: Filter to London, standardise borough names, remove outliers (IQR method), align datasets
3. **Analyse**: 9-phase Python pipeline computing metrics across multiple dimensions
4. **Visualise**: Tableau Public dashboards for interactive exploration

### 3.2 Key Metrics Computed

| Metric | Definition |
|--------|-----------|
| Median Price | Median transaction price per borough per year |
| Median Rent | Median monthly rent per borough per year |
| Gross Yield (%) | (Annual Rent / Median Price) × 100 |
| Price-to-Rent Ratio | Median Price / Annual Rent |
| YoY Growth (%) | Year-over-year percentage change |
| CAGR (%) | Compound Annual Growth Rate (2019–2024) |
| Price Index (2019=100) | Rebased price index for trend comparison |
| Rent Index (2019=100) | Rebased rent index for trend comparison |
| Rent vs Mortgage (%) | Monthly Rent / Estimated Monthly Mortgage × 100 |

### 3.3 Investment Scoring

Each borough receives a composite score based on:

| Component | Weight | Description |
|-----------|--------|-------------|
| Yield Score | ~50% | Normalised average gross yield (2019–2024) |
| Growth Score | ~50% | Normalised blend of price CAGR and rent CAGR |
| **Total Score** | 100% | Weighted combination → Recommendation |

**Recommendation thresholds:**
- **Buy**: Total Score ≥ 60
- **Hold**: Total Score 40–59
- **Watch**: Total Score < 40

---

## 4. Key Findings

### 4.1 Property Price Overview

- London median property price ranged from approximately **£310,000** (Barking and Dagenham) to **£1,300,000+** (Kensington and Chelsea) in 2024.
- **Detached** properties command the highest median price (~£890,000 in 2024), while **Flats/Maisonettes** are the most affordable (~£430,000).
- Property prices peaked in 2022 and saw a slight correction in 2023–2024 for most boroughs.

### 4.2 Rental Market Overview

- Monthly median rents range from approximately **£1,100** (outer boroughs) to **£2,500+** (central London).
- Rents have risen significantly since 2021, with some boroughs seeing **10%+ annual rent CAGR**.
- **4+ bedroom** properties command the highest rents (~£3,000/month in 2024).
- **Studios** remain the most affordable (~£1,350/month in 2024).

### 4.3 Investment Hotspots

**Top-scoring boroughs (Buy recommendation):**

Boroughs in **East** and **South** London consistently score highest due to:
- Higher gross rental yields (4–5%)
- Stronger price growth trajectories
- Lower entry prices enabling better yield percentages

**Lower-scoring boroughs (Watch recommendation):**

Prime **Central** and **West** London boroughs tend to score lower due to:
- Very high property prices suppressing yield percentages
- Slower relative price growth from an already high base

### 4.4 Affordability

- Boroughs with **rent-vs-mortgage ratio > 60%** suggest renting is relatively expensive compared to buying — these are potential buy opportunities.
- Boroughs with **rent-vs-mortgage ratio < 50%** suggest buying is more expensive — renting may be more practical.
- The **price-to-rent ratio** generally falls between 20–35 years across London boroughs.

### 4.5 Postcode-Level Insights

- Significant rent variation exists **within** boroughs at postcode level.
- Central postcodes (W1, WC1, EC, SW1) have the highest rents but limited data availability due to commercial dominance.
- 78 out of 292 London postcodes lack sufficient rental data for analysis.

---

## 5. Dashboard Summary

| Dashboard | Purpose | Key Interactions |
|-----------|---------|-----------------|
| **Overview** | High-level borough map and trends | Parameter toggle (Price/Rent), year filter, borough filter |
| **Investment Hotspot** | Identify best investment boroughs | Bubble chart (yield vs growth), ranking table, CAGR comparison |
| **Affordability** | Compare rent-vs-buy economics | Rent-to-mortgage ratio with average reference line, yield scatter |
| **Property Type & Rent** | Analyse by property type and room count | Dual trend lines for price types and rent room counts |
| **Postcode Rent** | Granular postcode-level rent distribution | Interactive map with filter, room count breakdown |

---

## 6. Technical Notes

### Tools Used

| Tool | Purpose |
|------|---------|
| Python 3 | Data pipeline (download, clean, analyse) |
| MySQL | Intermediate data processing for price cleaning |
| Pandas / NumPy | Data manipulation and statistical computation |
| Matplotlib / Seaborn | Data quality visualisation |
| Tableau Public | Interactive dashboards and storytelling |

### Reproducibility

The entire pipeline is automated and can be re-run with:

```bash
python main.py
```

New annual data can be incorporated by simply running the pipeline again — all scripts are designed for incremental updates.

---

## 7. Conclusion

This analysis reveals that London's property market is highly segmented by geography, property type, and price tier. Key takeaways:

1. **East and South London** offer the strongest investment fundamentals with higher yields and growth rates.
2. **Rental growth has outpaced price growth** in many boroughs since 2021, improving yield metrics.
3. **Affordability varies dramatically** — the rent-vs-mortgage ratio highlights boroughs where buying may be more economical than renting.
4. **Postcode-level data** reveals significant intra-borough variation that borough averages can mask.
5. **The market corrected in 2023–2024** after the 2022 peak, with most boroughs showing stabilising or slightly declining prices while rents continued to rise.

### Recommendations for Further Analysis

- Incorporate **crime rate data** for a safety-adjusted investment score
- Add **transport connectivity** (distance to tube stations) as a factor
- Include **new-build vs existing property** price segmentation

---

## 8. Data Disclaimer

**Property Price Data**: HM Land Registry Price Paid Data covers completed residential property transactions in England and Wales. Off-market and non-residential transactions are excluded.

**Rental Data**: ONS Private Rental Market Summary Statistics are based on a non-statistical sample from administrative data. The ONS states:

> "The sample used to produce these statistics is **not statistical** and may **not be consistent over time**, as such these data **should not be compared across time periods** or between areas."

All rental-based metrics (yield, rent trends, affordability) should be interpreted with this caveat in mind.

---

**Author**: Kerry Wu
**Tools**: Python, MySQL, Tableau Public
**Last Updated**: March 2026
