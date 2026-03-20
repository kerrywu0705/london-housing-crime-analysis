"""
London Property Market Analysis v7
Comprehensive analysis based on price_filtered (transaction-level) and rent_filtered (aggregated) data
Output: CSV reports organized by Tableau dashboard + data quality & analysis charts

Data sources:
- Price: price_YYYY_filtered.csv (transaction-level data)
  Fields: transaction_id, price, year, month, postcode, outward_code, property_type,
          status, duration, borough, direction, state, source_flag
- Rent Borough: rent_YYYY_borough.csv (Borough aggregated)
  Fields: year, borough, category, count, mean, median, lower_quartile, upper_quartile, direction
- Rent Postcode: rent_YYYY_postcode.csv (Postcode aggregated)
  Fields: year, postcode, category, count, mean, median, lower_quartile, upper_quartile, state

Analysis strategy:
- Price uses median aggregation to Borough level
- Rent uses ONS-provided median field
- Yield/Trend/Hotspot/Regional/Affordability -> Borough level
- Property type analysis -> Price (property_type) and Rent (category) separately

v6 Changes:
- Tableau CSV output organized by dashboard folders
- Added data quality charts (before/after cleaning)
- Analysis charts reorganized
- All paths updated to london_property
- All comments in English

v7 Changes:
- Removed analysis charts output (will be done in Tableau)
- Removed plot_analysis_charts function
"""

import os
import re
import warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path
from matplotlib.patches import Patch

# Suppress warnings
warnings.filterwarnings('ignore')

# ============================================================================
# Configuration
# ============================================================================

# Path settings
BASE_DIR = r"C:\Users\kerry\Desktop\london_property"
PRICE_DIR = os.path.join(BASE_DIR, "property_price_filtered")
RENT_DIR = os.path.join(BASE_DIR, "property_rent_filtered")
LOOKUP_DIR = os.path.join(BASE_DIR, "lookup_table")

# Raw data directories (for data quality charts)
PRICE_RAW_DIR = os.path.join(BASE_DIR, "property_price")
RENT_RAW_DIR = os.path.join(BASE_DIR, "property_rent")

# Output directories
TABLEAU_OUTPUT_DIR = os.path.join(BASE_DIR, "tableau_output")
IMAGES_OUTPUT_DIR = os.path.join(BASE_DIR, "images_output")

# Year range
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
BASE_YEAR = 2019

# Price Property Type (exclude 'O' = Other, non-residential)
PRICE_CATEGORY_ORDER = ['D', 'S', 'T', 'F']
PRICE_CATEGORY_LABELS = {
    'D': 'Detached',
    'S': 'Semi-detached',
    'T': 'Terraced',
    'F': 'Flat/Maisonette'
}

# Rent Room count
RENT_CATEGORY_ORDER = ['studio', '1_bed', '2_bed', '3_bed', '4_bed_plus']
RENT_CATEGORY_LABELS = {
    'studio': 'Studio',
    '1_bed': '1 Bedroom',
    '2_bed': '2 Bedrooms',
    '3_bed': '3 Bedrooms',
    '4_bed_plus': '4+ Bedrooms'
}

# Direction order
# Note: Exclude 'central' because City of London is the only Borough marked as central,
# primarily a financial district with very few residential transactions, insufficient sample size
DIRECTION_ORDER = ['north', 'south', 'east', 'west']

# Chart style settings
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['figure.dpi'] = 150
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10

# Color settings
COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'success': '#28A745',
    'warning': '#FFC107',
    'danger': '#DC3545',
    'info': '#17A2B8',
    'directions': {
        'central': '#E63946',
        'north': '#457B9D',
        'south': '#2A9D8F',
        'east': '#E9C46A',
        'west': '#F4A261'
    }
}

# Borough standard names (for Tableau geographic recognition)
BOROUGH_STANDARD_NAMES = {
    'barking and dagenham': 'Barking and Dagenham', 'barnet': 'Barnet', 'bexley': 'Bexley',
    'brent': 'Brent', 'bromley': 'Bromley', 'camden': 'Camden', 'croydon': 'Croydon',
    'ealing': 'Ealing', 'enfield': 'Enfield', 'greenwich': 'Greenwich', 'hackney': 'Hackney',
    'hammersmith and fulham': 'Hammersmith and Fulham', 'haringey': 'Haringey', 'harrow': 'Harrow',
    'havering': 'Havering', 'hillingdon': 'Hillingdon', 'hounslow': 'Hounslow', 'islington': 'Islington',
    'kensington and chelsea': 'Kensington and Chelsea', 'kingston upon thames': 'Kingston upon Thames',
    'lambeth': 'Lambeth', 'lewisham': 'Lewisham', 'merton': 'Merton', 'newham': 'Newham',
    'redbridge': 'Redbridge', 'richmond upon thames': 'Richmond upon Thames', 'southwark': 'Southwark',
    'sutton': 'Sutton', 'tower hamlets': 'Tower Hamlets', 'waltham forest': 'Waltham Forest',
    'wandsworth': 'Wandsworth', 'westminster': 'Westminster'
}

# ============================================================================
# Helper Functions
# ============================================================================

def standardize_borough_name(borough):
    """Standardize Borough name (for Tableau geographic recognition)"""
    return BOROUGH_STANDARD_NAMES.get(borough.lower().strip(), borough.title())


def add_date_column(df, year_col='year'):
    """Add date column for Tableau time series recognition"""
    if year_col in df.columns:
        df['date'] = pd.to_datetime(df[year_col].astype(str) + '-07-01')
        df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    return df


def weighted_median(values, weights):
    """Calculate weighted median"""
    values = np.array(values)
    weights = np.array(weights)

    # Sort
    sorted_idx = np.argsort(values)
    sorted_values = values[sorted_idx]
    sorted_weights = weights[sorted_idx]

    # Calculate cumulative weight
    cumsum = np.cumsum(sorted_weights)
    total = cumsum[-1]

    # Find median position
    median_idx = np.searchsorted(cumsum, total / 2)
    return sorted_values[min(median_idx, len(sorted_values) - 1)]


def weighted_quartile(values, weights, q):
    """Calculate weighted quartile (q=0.25 for Q1, q=0.75 for Q3)"""
    values = np.array(values)
    weights = np.array(weights)

    sorted_idx = np.argsort(values)
    sorted_values = values[sorted_idx]
    sorted_weights = weights[sorted_idx]

    cumsum = np.cumsum(sorted_weights)
    total = cumsum[-1]

    idx = np.searchsorted(cumsum, total * q)
    return sorted_values[min(idx, len(sorted_values) - 1)]


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_price_data():
    """Load property price data (transaction-level)"""
    print("Loading property price data...")
    all_data = []

    for year in YEARS:
        filepath = os.path.join(PRICE_DIR, f"price_{year}_filtered.csv")
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            all_data.append(df)
            print(f"  {year}: {len(df):,} transactions (Borough: {df['borough'].nunique()})")
        else:
            print(f"  {year}: File not found")

    if not all_data:
        print("  Error: No price data found")
        return None

    df = pd.concat(all_data, ignore_index=True)
    df.columns = df.columns.str.lower().str.strip()
    df['borough'] = df['borough'].str.lower().str.strip()
    df['direction'] = df['direction'].str.lower().str.strip()
    df['property_type'] = df['property_type'].str.upper().str.strip()

    # Filter out central (City of London)
    # Reason: Financial district with very few residential transactions
    central_count = len(df[df['direction'] == 'central'])
    df = df[df['direction'] != 'central']
    if central_count > 0:
        print(f"  Excluded central (City of London): {central_count:,} records")

    # Filter out Property Type = 'O' (Other)
    # Reason: Other type is not residential
    other_count = len(df[df['property_type'] == 'O'])
    df = df[df['property_type'] != 'O']
    if other_count > 0:
        print(f"  Excluded Property Type 'O' (Other, non-residential): {other_count:,} records")

    print(f"  Total: {len(df):,} transactions")
    print(f"  Borough: {df['borough'].nunique()}, Property Type: {sorted(df['property_type'].unique())}")
    return df


def load_rent_borough_data():
    """Load Borough-level rent data"""
    print("Loading Borough rent data...")
    all_data = []

    for year in YEARS:
        filepath = os.path.join(RENT_DIR, f"rent_{year}_borough.csv")
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            all_data.append(df)
            print(f"  {year}: {len(df)} records")
        else:
            print(f"  {year}: File not found")

    if not all_data:
        print("  Error: No rent data found")
        return None

    df = pd.concat(all_data, ignore_index=True)
    df.columns = df.columns.str.lower().str.strip()
    df['borough'] = df['borough'].str.lower().str.strip()
    df['direction'] = df['direction'].str.lower().str.strip()

    # Filter out central (City of London)
    central_count = len(df[df['direction'] == 'central'])
    df = df[df['direction'] != 'central']
    if central_count > 0:
        print(f"  Excluded central (City of London): {central_count} records")

    print(f"  Total: {len(df)} records")
    print(f"  Borough: {df['borough'].nunique()}, Category: {sorted(df['category'].unique())}")
    return df


def load_rent_postcode_data():
    """Load Postcode-level rent data"""
    print("Loading Postcode rent data...")
    all_data = []

    for year in YEARS:
        filepath = os.path.join(RENT_DIR, f"rent_{year}_postcode.csv")
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            all_data.append(df)
            print(f"  {year}: {len(df)} records")
        else:
            print(f"  {year}: File not found")

    if not all_data:
        print("  Warning: No Postcode rent data found")
        return None

    df = pd.concat(all_data, ignore_index=True)
    df.columns = df.columns.str.lower().str.strip()

    print(f"  Total: {len(df)} records")
    return df


def load_raw_price_sample(year=2024, sample_size=100000):
    """Load raw price data sample for data quality comparison"""
    print(f"Loading raw price data sample ({year})...")
    filepath = os.path.join(PRICE_RAW_DIR, f"pp-{year}.csv")

    if not os.path.exists(filepath):
        print(f"  Warning: Raw file not found: {filepath}")
        return None

    try:
        # Read only London data (filter by county)
        df = pd.read_csv(filepath, low_memory=False)
        df.columns = df.columns.str.lower().str.strip()

        # Filter for Greater London
        if 'county' in df.columns:
            london_df = df[df['county'].str.upper().str.contains('LONDON', na=False)]
        else:
            london_df = df

        print(f"  Raw records: {len(df):,}, London records: {len(london_df):,}")
        return london_df.head(sample_size) if len(london_df) > sample_size else london_df
    except Exception as e:
        print(f"  Error loading raw data: {e}")
        return None


# ============================================================================
# Borough Aggregation Functions
# ============================================================================

def aggregate_price_to_borough(price_data):
    """Aggregate transaction-level price data to Borough level (using median)"""
    price_borough = price_data.groupby(['year', 'borough', 'direction', 'state']).agg(
        price_count=('price', 'count'),
        price_median=('price', 'median'),
        price_mean=('price', 'mean'),
        price_q1=('price', lambda x: x.quantile(0.25)),
        price_q3=('price', lambda x: x.quantile(0.75))
    ).reset_index()

    return price_borough


def aggregate_rent_to_borough(rent_data):
    """Aggregate rent data to Borough level (weighted median)"""
    rent_borough = rent_data.groupby(['year', 'borough', 'direction']).apply(
        lambda x: pd.Series({
            'rent_count': x['count'].sum(),
            'rent_median': weighted_median(x['median'], x['count']),
            'rent_mean': np.average(x['mean'], weights=x['count']),
            'rent_q1': weighted_quartile(x['lower_quartile'], x['count'], 0.25),
            'rent_q3': weighted_quartile(x['upper_quartile'], x['count'], 0.75)
        })
    ).reset_index()

    return rent_borough


def merge_price_rent_borough(price_borough, rent_borough):
    """Merge price and rent Borough-level data"""
    # Price may have state column, aggregate it first
    price_agg = price_borough.groupby(['year', 'borough', 'direction']).agg({
        'price_count': 'sum',
        'price_median': 'median',
        'price_mean': 'mean',
        'price_q1': 'median',
        'price_q3': 'median'
    }).reset_index()

    # Merge
    merged = pd.merge(price_agg, rent_borough,
                      on=['year', 'borough', 'direction'], how='inner')

    return merged


# ============================================================================
# Data Quality Charts (NEW in v6)
# ============================================================================

def plot_data_quality_charts(price_data, rent_data, raw_price_data, output_dir):
    """Plot data quality charts showing before/after cleaning comparison"""
    print("\n" + "=" * 60)
    print("Phase 2: Data Quality Charts")
    print("=" * 60)

    chart_dir = os.path.join(output_dir, "data_quality")
    os.makedirs(chart_dir, exist_ok=True)

    latest_year = price_data['year'].max()
    latest_price = price_data[price_data['year'] == latest_year]

    # Chart 1: Price Distribution Before vs After Cleaning
    print("  - 01_price_distribution_comparison.png")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    if raw_price_data is not None and 'price' in raw_price_data.columns:
        # Before cleaning
        raw_prices = raw_price_data['price'].dropna()
        raw_prices = raw_prices[raw_prices > 0]

        axes[0].hist(raw_prices / 1000, bins=100, color=COLORS['danger'], alpha=0.7, edgecolor='white')
        axes[0].set_xlabel('Price (£k)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title(f'Before Cleaning (n={len(raw_prices):,})')
        axes[0].set_xlim(0, 5000)

        # Add statistics
        stats_text = f'Mean: £{raw_prices.mean()/1000:.0f}k\nMedian: £{raw_prices.median()/1000:.0f}k\nMax: £{raw_prices.max()/1000:.0f}k'
        axes[0].text(0.95, 0.95, stats_text, transform=axes[0].transAxes, fontsize=10,
                     verticalalignment='top', horizontalalignment='right',
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # After cleaning
    clean_prices = latest_price['price'].dropna()
    axes[1].hist(clean_prices / 1000, bins=100, color=COLORS['success'], alpha=0.7, edgecolor='white')
    axes[1].set_xlabel('Price (£k)')
    axes[1].set_ylabel('Frequency')
    axes[1].set_title(f'After Cleaning (n={len(clean_prices):,})')
    axes[1].set_xlim(0, 5000)

    # Add statistics
    stats_text = f'Mean: £{clean_prices.mean()/1000:.0f}k\nMedian: £{clean_prices.median()/1000:.0f}k\nMax: £{clean_prices.max()/1000:.0f}k'
    axes[1].text(0.95, 0.95, stats_text, transform=axes[1].transAxes, fontsize=10,
                 verticalalignment='top', horizontalalignment='right',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.suptitle(f'Price Distribution Before vs After Cleaning ({latest_year})', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, "01_price_distribution_comparison.png"))
    plt.close()

    # Chart 2: Log-transformed Price Distribution
    print("  - 02_price_log_distribution.png")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    if raw_price_data is not None and 'price' in raw_price_data.columns:
        raw_prices = raw_price_data['price'].dropna()
        raw_prices = raw_prices[raw_prices > 0]

        axes[0].hist(np.log10(raw_prices), bins=50, color=COLORS['danger'], alpha=0.7, edgecolor='white')
        axes[0].set_xlabel('Log10(Price)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Before Cleaning (Log Scale)')

    axes[1].hist(np.log10(clean_prices), bins=50, color=COLORS['success'], alpha=0.7, edgecolor='white')
    axes[1].set_xlabel('Log10(Price)')
    axes[1].set_ylabel('Frequency')
    axes[1].set_title('After Cleaning (Log Scale)')

    plt.suptitle(f'Price Distribution (Log Scale) - {latest_year}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, "02_price_log_distribution.png"))
    plt.close()

    # Chart 3: Boxplot Before vs After
    print("  - 03_price_boxplot_comparison.png")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    if raw_price_data is not None and 'price' in raw_price_data.columns:
        raw_prices = raw_price_data['price'].dropna()
        raw_prices = raw_prices[(raw_prices > 0) & (raw_prices < raw_prices.quantile(0.99))]

        bp1 = axes[0].boxplot([raw_prices / 1000], patch_artist=True, showfliers=True)
        bp1['boxes'][0].set_facecolor(COLORS['danger'])
        bp1['boxes'][0].set_alpha(0.7)
        axes[0].set_ylabel('Price (£k)')
        axes[0].set_title('Before Cleaning')
        axes[0].set_xticklabels(['All Data'])

    bp2 = axes[1].boxplot([clean_prices / 1000], patch_artist=True, showfliers=True)
    bp2['boxes'][0].set_facecolor(COLORS['success'])
    bp2['boxes'][0].set_alpha(0.7)
    axes[1].set_ylabel('Price (£k)')
    axes[1].set_title('After Cleaning')
    axes[1].set_xticklabels(['London Only'])

    plt.suptitle(f'Price Boxplot Comparison ({latest_year})', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, "03_price_boxplot_comparison.png"))
    plt.close()

    # Chart 4: Transaction Count by Borough
    print("  - 04_transaction_count_by_borough.png")
    fig, ax = plt.subplots(figsize=(14, 10))

    borough_counts = latest_price.groupby('borough').size().sort_values(ascending=True)
    colors = [COLORS['primary'] if c > borough_counts.median() else COLORS['warning']
              for c in borough_counts.values]

    ax.barh(borough_counts.index.str.title(), borough_counts.values, color=colors)
    ax.set_xlabel('Number of Transactions')
    ax.set_title(f'Transaction Count by Borough ({latest_year})')
    ax.axvline(x=borough_counts.median(), color='red', linestyle='--',
               label=f'Median: {borough_counts.median():.0f}')
    ax.legend()

    # Add count labels
    for i, v in enumerate(borough_counts.values):
        ax.text(v + 50, i, f'{v:,}', va='center', fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, "04_transaction_count_by_borough.png"))
    plt.close()

    # Chart 5: Property Type Distribution
    print("  - 05_property_type_distribution.png")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Pie chart
    type_counts = latest_price['property_type'].value_counts()
    type_labels = [PRICE_CATEGORY_LABELS.get(t, t) for t in type_counts.index]
    colors_pie = [COLORS['primary'], COLORS['secondary'], COLORS['success'], COLORS['warning']]

    axes[0].pie(type_counts.values, labels=type_labels, autopct='%1.1f%%',
                colors=colors_pie[:len(type_counts)], startangle=90)
    axes[0].set_title('Distribution by Property Type')

    # Bar chart with count
    axes[1].bar(type_labels, type_counts.values, color=colors_pie[:len(type_counts)])
    axes[1].set_ylabel('Number of Transactions')
    axes[1].set_title('Transaction Count by Property Type')

    for i, v in enumerate(type_counts.values):
        axes[1].text(i, v + 100, f'{v:,}', ha='center', fontsize=10)

    plt.suptitle(f'Property Type Distribution ({latest_year})', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, "05_property_type_distribution.png"))
    plt.close()

    # Chart 6: Yearly Transaction Trend
    print("  - 06_yearly_transaction_trend.png")
    fig, ax = plt.subplots(figsize=(12, 6))

    yearly_counts = price_data.groupby('year').size()

    bars = ax.bar(yearly_counts.index, yearly_counts.values, color=COLORS['primary'], alpha=0.8)
    ax.set_xlabel('Year')
    ax.set_ylabel('Number of Transactions')
    ax.set_title('Yearly Transaction Volume (London)')

    # Highlight COVID years
    for bar in bars:
        year = bar.get_x() + bar.get_width() / 2
        if year in [2020, 2021]:
            bar.set_color(COLORS['warning'])

    # Add count labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 500,
                f'{int(height):,}', ha='center', va='bottom', fontsize=10)

    # Add COVID annotation
    ax.annotate('COVID-19\nImpact', xy=(2020.5, yearly_counts.loc[2020]),
                xytext=(2020.5, yearly_counts.loc[2020] + 15000),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color='gray'))

    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, "06_yearly_transaction_trend.png"))
    plt.close()

    print("  Data quality charts completed!")


# ============================================================================
# Analysis Functions
# ============================================================================

def calculate_yield(price_data, rent_data, rent_postcode):
    """Calculate rental yield (Borough level)"""
    print("\n" + "=" * 60)
    print("Phase 3: Calculate Yield Metrics")
    print("=" * 60)

    # Aggregate price to Borough level
    print("\nAggregating price to Borough level...")
    price_borough = aggregate_price_to_borough(price_data)
    print(f"  Price Borough records: {len(price_borough)}")

    # Aggregate rent to Borough level
    print("Aggregating rent to Borough level...")
    rent_borough = aggregate_rent_to_borough(rent_data)
    print(f"  Rent Borough records: {len(rent_borough)}")

    # Merge price and rent
    print("Merging price and rent...")
    yield_data = merge_price_rent_borough(price_borough, rent_borough)

    # Calculate yield metrics
    yield_data['annual_rent'] = yield_data['rent_median'] * 12
    yield_data['gross_yield_pct'] = (yield_data['annual_rent'] / yield_data['price_median'] * 100).round(2)
    yield_data['price_to_rent_ratio'] = (yield_data['price_median'] / yield_data['annual_rent']).round(1)

    # Remove outliers
    yield_data = yield_data[
        (yield_data['gross_yield_pct'] > 0) &
        (yield_data['gross_yield_pct'] < 20) &
        (yield_data['price_median'] > 0) &
        (yield_data['rent_median'] > 0)
    ]

    print(f"  Borough yield records: {len(yield_data)}")

    # Postcode level
    yield_postcode = None
    if rent_postcode is not None:
        print("\nCalculating Postcode rent aggregation...")
        yield_postcode = rent_postcode.copy()
        yield_postcode['annual_rent'] = yield_postcode['median'] * 12
        yield_postcode = yield_postcode.rename(columns={'median': 'rent_median'})
        print(f"  Postcode records: {len(yield_postcode)}")

    return yield_data, yield_postcode, price_borough


def calculate_trend(yield_data):
    """Calculate price trend (Borough level)"""
    print("\n" + "=" * 60)
    print("Phase 4: Calculate Trend Metrics")
    print("=" * 60)

    trend_data = yield_data.copy()

    # Calculate base year data
    base_data = trend_data[trend_data['year'] == BASE_YEAR][['borough', 'price_median', 'rent_median']].copy()
    base_data = base_data.rename(columns={'price_median': 'price_base', 'rent_median': 'rent_base'})

    # Add base year data
    trend_data = pd.merge(trend_data, base_data, on='borough', how='left')

    # Calculate index
    trend_data['price_index_2019'] = (trend_data['price_median'] / trend_data['price_base'] * 100).round(1)
    trend_data['rent_index_2019'] = (trend_data['rent_median'] / trend_data['rent_base'] * 100).round(1)

    # Calculate growth percentage (2019=0%)
    trend_data['price_growth_pct'] = (trend_data['price_index_2019'] - 100).round(1)
    trend_data['rent_growth_pct'] = (trend_data['rent_index_2019'] - 100).round(1)

    # Calculate YoY
    trend_data = trend_data.sort_values(['borough', 'year'])
    trend_data['price_prev'] = trend_data.groupby('borough')['price_median'].shift(1)
    trend_data['rent_prev'] = trend_data.groupby('borough')['rent_median'].shift(1)
    trend_data['price_yoy_pct'] = ((trend_data['price_median'] - trend_data['price_prev']) / trend_data['price_prev'] * 100).round(2)
    trend_data['rent_yoy_pct'] = ((trend_data['rent_median'] - trend_data['rent_prev']) / trend_data['rent_prev'] * 100).round(2)

    # Clean up
    trend_data = trend_data.drop(columns=['price_base', 'rent_base', 'price_prev', 'rent_prev'], errors='ignore')

    print(f"  Borough trend records: {len(trend_data)}")

    return trend_data


def calculate_hotspot(yield_data, trend_data):
    """Calculate investment hotspot"""
    print("\n" + "=" * 60)
    print("Phase 5: Calculate Hotspot Metrics")
    print("=" * 60)

    # Calculate 3-year average yield
    max_year = yield_data['year'].max()
    recent_yield = yield_data[yield_data['year'] >= max_year - 2]

    borough_yield = recent_yield.groupby('borough').agg({
        'gross_yield_pct': 'mean',
        'direction': 'first'
    }).reset_index()
    borough_yield.columns = ['borough', 'avg_yield_pct', 'direction']

    # Calculate CAGR
    first_year = trend_data['year'].min()
    last_year = trend_data['year'].max()
    n_years = last_year - first_year

    if n_years > 0:
        first_data = trend_data[trend_data['year'] == first_year].groupby('borough')[['price_median', 'rent_median']].median()
        last_data = trend_data[trend_data['year'] == last_year].groupby('borough')[['price_median', 'rent_median']].median()

        common_boroughs = first_data.index.intersection(last_data.index)

        cagr_list = []
        for borough in common_boroughs:
            price_cagr = ((last_data.loc[borough, 'price_median'] / first_data.loc[borough, 'price_median']) ** (1/n_years) - 1) * 100
            rent_cagr = ((last_data.loc[borough, 'rent_median'] / first_data.loc[borough, 'rent_median']) ** (1/n_years) - 1) * 100
            cagr_list.append({'borough': borough, 'price_cagr_pct': price_cagr, 'rent_cagr_pct': rent_cagr})

        cagr = pd.DataFrame(cagr_list)
    else:
        cagr = pd.DataFrame(columns=['borough', 'price_cagr_pct', 'rent_cagr_pct'])

    # Merge
    hotspot = pd.merge(borough_yield, cagr, on='borough', how='inner')

    if len(hotspot) == 0:
        print("  Warning: Cannot calculate hotspot analysis")
        return pd.DataFrame()

    # Calculate scores
    yield_range = hotspot['avg_yield_pct'].max() - hotspot['avg_yield_pct'].min()
    growth_range = hotspot['price_cagr_pct'].max() - hotspot['price_cagr_pct'].min()

    if yield_range > 0:
        hotspot['yield_score'] = ((hotspot['avg_yield_pct'] - hotspot['avg_yield_pct'].min()) / yield_range * 100).round(1)
    else:
        hotspot['yield_score'] = 50

    if growth_range > 0:
        hotspot['growth_score'] = ((hotspot['price_cagr_pct'] - hotspot['price_cagr_pct'].min()) / growth_range * 100).round(1)
    else:
        hotspot['growth_score'] = 50

    hotspot['total_score'] = (hotspot['yield_score'] * 0.5 + hotspot['growth_score'] * 0.5).round(1)

    # Recommendation level
    def get_recommendation(score):
        if score >= 70:
            return 'Strong Buy'
        elif score >= 50:
            return 'Buy'
        elif score >= 30:
            return 'Hold'
        else:
            return 'Avoid'

    hotspot['recommendation'] = hotspot['total_score'].apply(get_recommendation)

    # Round
    hotspot['avg_yield_pct'] = hotspot['avg_yield_pct'].round(2)
    hotspot['price_cagr_pct'] = hotspot['price_cagr_pct'].round(2)
    hotspot['rent_cagr_pct'] = hotspot['rent_cagr_pct'].round(2)

    print(f"  Hotspot analysis records: {len(hotspot)}")
    print(f"  Recommendation distribution: {hotspot['recommendation'].value_counts().to_dict()}")

    return hotspot


def calculate_affordability(yield_data):
    """Calculate affordability metrics"""
    print("\n" + "=" * 60)
    print("Phase 6: Calculate Affordability Metrics")
    print("=" * 60)

    afford = yield_data.copy()

    # Price to rent ratio (years of rent to buy)
    afford['price_to_rent_years'] = (afford['price_median'] / afford['annual_rent']).round(1)

    # Estimated monthly mortgage (30-year term, 4.5% interest rate, 75% LTV)
    rate = 0.045 / 12
    n_payments = 30 * 12
    ltv = 0.75
    afford['monthly_mortgage_est'] = (
        afford['price_median'] * ltv * (rate * (1 + rate)**n_payments) / ((1 + rate)**n_payments - 1)
    ).round(0)

    # Rent vs mortgage ratio
    afford['rent_vs_mortgage_pct'] = (afford['rent_median'] / afford['monthly_mortgage_est'] * 100).round(1)

    print(f"  Affordability records: {len(afford)}")

    return afford


def calculate_property_type(price_data, rent_data):
    """Calculate property type analysis (price and rent separately)"""
    print("\n" + "=" * 60)
    print("Phase 7: Calculate Property Type Metrics")
    print("=" * 60)

    # Price Property Type aggregation (from transaction-level data)
    print("\nAggregating Price Property Type...")
    price_type = price_data.groupby(['year', 'property_type']).agg(
        transaction_count=('price', 'count'),
        avg_price=('price', 'mean'),
        median_price=('price', 'median')
    ).reset_index()
    price_type = price_type.rename(columns={'property_type': 'category'})
    price_type['category_label'] = price_type['category'].map(PRICE_CATEGORY_LABELS)
    price_type['data_type'] = 'price'

    # Rent Room count aggregation (from aggregated data, using weights)
    print("Aggregating Rent Room count...")
    rent_type = rent_data.groupby(['year', 'category']).apply(
        lambda x: pd.Series({
            'listing_count': x['count'].sum(),
            'avg_rent': np.average(x['mean'], weights=x['count']),
            'median_rent': weighted_median(x['median'], x['count'])
        })
    ).reset_index()
    rent_type['category_label'] = rent_type['category'].map(RENT_CATEGORY_LABELS)
    rent_type['data_type'] = 'rent'

    print(f"  Price Property Type: {len(price_type)} records")
    print(f"  Rent Room count: {len(rent_type)} records")

    return price_type, rent_type


def create_postcode_map_data(rent_postcode):
    """Create Postcode map data"""
    print("\n" + "=" * 60)
    print("Phase 8: Create Postcode Map Data")
    print("=" * 60)

    if rent_postcode is None or len(rent_postcode) == 0:
        print("  Warning: No Postcode rent data")
        return None

    coord_file = os.path.join(LOOKUP_DIR, "outward_code_coordinates.csv")
    if not os.path.exists(coord_file):
        print(f"  Warning: Coordinate file not found: {coord_file}")
        return None

    coords = pd.read_csv(coord_file)
    print(f"  Coordinate lookup: {len(coords)} records")

    rent_copy = rent_postcode.copy()
    rent_copy['postcode'] = rent_copy['postcode'].str.upper().str.strip()
    coords['outward_code'] = coords['outward_code'].str.upper().str.strip()

    postcode_map = pd.merge(rent_copy, coords, left_on='postcode', right_on='outward_code', how='left')

    matched = postcode_map['latitude'].notna().sum()
    print(f"  Coordinate match: {matched}/{len(postcode_map)} ({matched/len(postcode_map)*100:.1f}%)")

    postcode_map = add_date_column(postcode_map)
    postcode_map['category_label'] = postcode_map['category'].map(RENT_CATEGORY_LABELS)

    # Aggregated map data
    postcode_agg = postcode_map.groupby(['year', 'postcode', 'latitude', 'longitude', 'area_name']).agg(
        listing_count=('count', 'sum'),
        rent_median=('rent_median', 'median'),
        rent_mean=('mean', 'mean')
    ).reset_index()
    postcode_agg = add_date_column(postcode_agg)

    print(f"  Postcode map: {len(postcode_agg)} records, Detail: {len(postcode_map)} records")

    return {'map': postcode_agg, 'detail': postcode_map}


# ============================================================================
# Tableau Export
# ============================================================================

def export_tableau_csvs(trend_data, hotspot, afford, price_type, rent_type, postcode_data, output_dir):
    """Export Tableau-optimized CSVs to output directory (each CSV in its own subfolder)"""
    print("\n" + "=" * 60)
    print("Phase 9: Export Tableau CSVs")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)

    def save_csv(df, subfolder, filename):
        """Save CSV to its own subfolder to avoid Tableau multi-connection issues"""
        folder = os.path.join(output_dir, subfolder)
        os.makedirs(folder, exist_ok=True)
        df.to_csv(os.path.join(folder, filename), index=False, encoding='utf-8')

    # Master Borough (Dashboard 1: Overview)
    master = add_date_column(trend_data.copy())
    master['borough_display'] = master['borough'].apply(standardize_borough_name)
    master['direction_display'] = master['direction'].str.capitalize()
    save_csv(master, "master_borough", "master_borough.csv")
    print(f"  master_borough/master_borough.csv ({len(master)} records)")

    # Hotspot Borough (Dashboard 2: Investment Hotspot)
    if len(hotspot) > 0:
        hs = hotspot.copy()
        hs['borough_display'] = hs['borough'].apply(standardize_borough_name)
        hs['direction_display'] = hs['direction'].str.capitalize()
        save_csv(hs, "hotspot_borough", "hotspot_borough.csv")
        print(f"  hotspot_borough/hotspot_borough.csv ({len(hs)} records)")

    # Affordability (Dashboard 3)
    aff = add_date_column(afford.copy())
    aff['borough_display'] = aff['borough'].apply(standardize_borough_name)
    aff['direction_display'] = aff['direction'].str.capitalize()
    save_csv(aff, "affordability", "affordability.csv")
    print(f"  affordability/affordability.csv ({len(aff)} records)")

    # Property Type (Dashboard 4)
    save_csv(add_date_column(price_type.copy()), "price_by_type", "price_by_type.csv")
    save_csv(add_date_column(rent_type.copy()), "rent_by_room", "rent_by_room.csv")
    print(f"  price_by_type/price_by_type.csv ({len(price_type)} records)")
    print(f"  rent_by_room/rent_by_room.csv ({len(rent_type)} records)")

    # Postcode (Dashboard 5)
    if postcode_data:
        if postcode_data.get('map') is not None:
            save_csv(postcode_data['map'], "postcode_map", "postcode_map.csv")
            print(f"  postcode_map/postcode_map.csv ({len(postcode_data['map'])} records)")
        if postcode_data.get('detail') is not None:
            save_csv(postcode_data['detail'], "postcode_detail", "postcode_detail.csv")
            print(f"  postcode_detail/postcode_detail.csv ({len(postcode_data['detail'])} records)")

    # Lookup tables
    lookups = {
        'borough': pd.DataFrame([{'borough_key': k, 'borough_display': v} for k, v in BOROUGH_STANDARD_NAMES.items()]),
        'direction': pd.DataFrame([{'direction': d, 'display': d.capitalize(), 'color': COLORS['directions'].get(d)} for d in DIRECTION_ORDER]),
        'property_type': pd.DataFrame([{'code': k, 'label': v, 'order': i} for i, (k, v) in enumerate(PRICE_CATEGORY_LABELS.items())]),
        'room_count': pd.DataFrame([{'code': k, 'label': v, 'order': i} for i, (k, v) in enumerate(RENT_CATEGORY_LABELS.items())])
    }

    lookup_dir = os.path.join(output_dir, "lookup")
    os.makedirs(lookup_dir, exist_ok=True)
    for name, df in lookups.items():
        df.to_csv(os.path.join(lookup_dir, f"lookup_{name}.csv"), index=False, encoding='utf-8')
    print("  lookup/lookup_*.csv exported")

    print("\nTableau CSV export completed!")


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 60)
    print("London Property Market Analysis v7")
    print("=" * 60)

    # Create output directories
    os.makedirs(TABLEAU_OUTPUT_DIR, exist_ok=True)
    os.makedirs(IMAGES_OUTPUT_DIR, exist_ok=True)

    # ========== Phase 1: Load Data ==========
    print("\n" + "=" * 60)
    print("Phase 1: Load Data")
    print("=" * 60)

    price_data = load_price_data()
    rent_data = load_rent_borough_data()
    rent_postcode = load_rent_postcode_data()

    if price_data is None or rent_data is None:
        print("\nError: Cannot load required data, please check file paths")
        return

    # Load raw data sample for data quality comparison
    raw_price_data = load_raw_price_sample(year=2024)

    # ========== Phase 2: Data Quality Charts ==========
    plot_data_quality_charts(price_data, rent_data, raw_price_data, IMAGES_OUTPUT_DIR)

    # ========== Phase 3-8: Calculate Metrics ==========
    yield_data, yield_postcode, price_borough = calculate_yield(price_data, rent_data, rent_postcode)
    trend_data = calculate_trend(yield_data)
    hotspot = calculate_hotspot(yield_data, trend_data)
    afford = calculate_affordability(yield_data)
    price_type, rent_type = calculate_property_type(price_data, rent_data)
    postcode_data = create_postcode_map_data(yield_postcode)

    # ========== Phase 9: Export Tableau CSVs ==========
    export_tableau_csvs(trend_data, hotspot, afford, price_type, rent_type, postcode_data, TABLEAU_OUTPUT_DIR)

    # ========== Summary ==========
    print("\n" + "=" * 60)
    print("Analysis Complete!")
    print("=" * 60)
    print(f"\nTableau CSV location: {TABLEAU_OUTPUT_DIR}")
    print(f"Charts location: {IMAGES_OUTPUT_DIR}")

    # Output summary
    print("\nOutput Summary:")
    print("-" * 40)

    print("\nTableau CSV files:")
    csv_files = [f for f in os.listdir(TABLEAU_OUTPUT_DIR) if f.endswith('.csv')]
    for f in sorted(csv_files):
        fpath = os.path.join(TABLEAU_OUTPUT_DIR, f)
        df = pd.read_csv(fpath)
        print(f"  - {f} ({len(df)} records)")

    print("\nData quality charts:")
    dq_folder = os.path.join(IMAGES_OUTPUT_DIR, "data_quality")
    if os.path.isdir(dq_folder):
        chart_count = len([f for f in os.listdir(dq_folder) if f.endswith('.png')])
        print(f"  - data_quality/ ({chart_count} charts)")


if __name__ == "__main__":
    main()
