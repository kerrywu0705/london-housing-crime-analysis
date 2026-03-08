"""
ONS Private Rental Market in London - Data Cleaning Script v2
Features: Clean rental data, standardize format, align with property price data
Changes: postcode_district renamed to postcode, filter postcodes not in outward_code_table
Output: Separate CSV files for Borough and Postcode data
"""

import os
import re
import pandas as pd
import numpy as np
import configparser

# ============================================================================
# Configuration
# ============================================================================

# Default paths (can be overridden by config.ini)
DEFAULT_RENT_DIR = r"C:\Users\kerry\Desktop\london_property\property_rent"
DEFAULT_OUTPUT_DIR = r"C:\Users\kerry\Desktop\london_property\property_rent_filtered"
DEFAULT_LOOKUP_DIR = r"C:\Users\kerry\Desktop\london_property\lookup_table"

# Sheet name settings (unified by download_rent.py after cleaning)
# 2019-2022: Table 1.2, Table 1.3
# 2023+: 2, 3
BOROUGH_SHEETS = ['Table 1.2', '2']
POSTCODE_SHEETS = ['Table 1.3', '3']

# Borough name mapping (ONS format → Standard format)
BOROUGH_NAME_MAPPING = {
    'city of westminster': 'westminster',
    'city of london': 'city of london',  # Will be filtered out
    'barking & dagenham': 'barking and dagenham',
    'barking and dagenham': 'barking and dagenham',
    'hammersmith & fulham': 'hammersmith and fulham',
    'hammersmith and fulham': 'hammersmith and fulham',
    'kensington & chelsea': 'kensington and chelsea',
    'kensington and chelsea': 'kensington and chelsea',
    'richmond upon thames': 'richmond upon thames',
    'kingston upon thames': 'kingston upon thames',
}

# Category standardization mapping
CATEGORY_MAPPING = {
    'room': 'room',
    'rooms': 'room',
    'studio': 'studio',
    'studios': 'studio',
    'one bedroom': '1_bed',
    '1 bedroom': '1_bed',
    '1 bed': '1_bed',
    '1bed': '1_bed',
    'two bedrooms': '2_bed',
    '2 bedrooms': '2_bed',
    '2 bed': '2_bed',
    '2bed': '2_bed',
    'three bedrooms': '3_bed',
    '3 bedrooms': '3_bed',
    '3 bed': '3_bed',
    '3bed': '3_bed',
    'four or more bedrooms': '4_bed_plus',
    'four+ bedrooms': '4_bed_plus',
    '4+ bedrooms': '4_bed_plus',
    '4 bedrooms': '4_bed_plus',
    '4 bed': '4_bed_plus',
    '4bed': '4_bed_plus',
    '4+ bed': '4_bed_plus',
}

# Categories to exclude
EXCLUDED_CATEGORIES = ['room']

# ============================================================================
# Load Configuration
# ============================================================================

def load_config(config_path='config.ini'):
    """Load configuration file"""
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path, encoding='utf-8')
    return config

def get_paths(config):
    """Get path settings"""
    if config and 'paths' in config:
        rent_dir = config['paths'].get('property_rent_dir', DEFAULT_RENT_DIR)
        output_dir = config['paths'].get('property_rent_filtered_dir', DEFAULT_OUTPUT_DIR)
        lookup_dir = config['paths'].get('lookup_table_dir', DEFAULT_LOOKUP_DIR)
    else:
        rent_dir = DEFAULT_RENT_DIR
        output_dir = DEFAULT_OUTPUT_DIR
        lookup_dir = DEFAULT_LOOKUP_DIR

    return rent_dir, output_dir, lookup_dir

# ============================================================================
# Read Excel
# ============================================================================

def find_sheet(excel_file, sheet_candidates):
    """Find existing sheet from candidate list"""
    available_sheets = excel_file.sheet_names
    for sheet in sheet_candidates:
        if sheet in available_sheets:
            return sheet
    return None

def standardize_columns(df, data_type):
    """Standardize column names"""
    # Clean column names (remove newlines and extra spaces)
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

    # Build column name mapping
    col_mapping = {}

    for col in df.columns:
        col_lower = str(col).lower().strip()

        # Borough column (only for borough data)
        if data_type == 'borough':
            if any(keyword in col_lower for keyword in ['borough', 'area', 'local authority', 'la name']):
                if 'borough' not in col_mapping.values():
                    col_mapping[col] = 'borough'

        # Postcode column (only for postcode data)
        if data_type == 'postcode':
            if any(keyword in col_lower for keyword in ['postcode', 'district']):
                if 'postcode' not in col_mapping.values():
                    col_mapping[col] = 'postcode'

        # Category column
        if any(keyword in col_lower for keyword in ['category', 'bedroom', 'room category']):
            if 'category' not in col_mapping.values():
                col_mapping[col] = 'category'

        # Count column
        elif 'count' in col_lower:
            if 'count' not in col_mapping.values():
                col_mapping[col] = 'count'

        # Mean column (ensure not median)
        elif 'mean' in col_lower and 'median' not in col_lower:
            if 'mean' not in col_mapping.values():
                col_mapping[col] = 'mean'

        # Median column
        elif 'median' in col_lower:
            if 'median' not in col_mapping.values():
                col_mapping[col] = 'median'

        # Lower Quartile column
        elif ('lower' in col_lower and 'quartile' in col_lower) or 'lq' in col_lower:
            if 'lower_quartile' not in col_mapping.values():
                col_mapping[col] = 'lower_quartile'

        # Upper Quartile column
        elif ('upper' in col_lower and 'quartile' in col_lower) or 'uq' in col_lower:
            if 'upper_quartile' not in col_mapping.values():
                col_mapping[col] = 'upper_quartile'

    df = df.rename(columns=col_mapping)

    return df

def read_sheet_data(filepath, sheet_name, data_type, year):
    """Read data from specified sheet"""
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=0)

        # Remove completely empty rows and columns
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')

        # Standardize column names
        df = standardize_columns(df, data_type)

        # Add year
        df['year'] = year

        return df

    except Exception as e:
        print(f"    Error: {e}")
        return None

# ============================================================================
# Data Cleaning
# ============================================================================

def load_borough_mapping(lookup_dir):
    """Load Borough mapping table"""
    filepath = os.path.join(lookup_dir, 'borough_mapping.csv')

    if not os.path.exists(filepath):
        print(f"Warning: Cannot find {filepath}")
        return None, None

    df = pd.read_csv(filepath)

    # Build valid borough list (lowercase)
    valid_boroughs = set(df['borough'].str.lower().tolist())

    # Build borough → direction mapping
    direction_map = dict(zip(
        df['borough'].str.lower(),
        df['direction']
    ))

    return valid_boroughs, direction_map

def load_outward_code_mapping(lookup_dir):
    """Load Outward Code mapping table"""
    filepath = os.path.join(lookup_dir, 'outward_code_table.csv')

    if not os.path.exists(filepath):
        print(f"Warning: Cannot find {filepath}")
        return None, None

    df = pd.read_csv(filepath)

    # Check column names
    columns = [c.lower() for c in df.columns]

    # Find outward_code column
    code_col = None
    for c in df.columns:
        if 'outward' in c.lower() or 'code' in c.lower() or 'postcode' in c.lower():
            code_col = c
            break

    if code_col is None:
        code_col = df.columns[0]  # Use first column

    # Find state column
    state_col = None
    for c in df.columns:
        if 'state' in c.lower() or 'area' in c.lower() or 'type' in c.lower():
            state_col = c
            break

    if state_col is None and len(df.columns) > 1:
        state_col = df.columns[1]  # Use second column

    print(f"  Outward Code column: {code_col}, State column: {state_col}")

    # Clean possible carriage return characters
    df[code_col] = df[code_col].astype(str).str.strip()
    if state_col:
        df[state_col] = df[state_col].astype(str).str.strip()

    # Build valid postcode list
    valid_postcodes = set(df[code_col].str.upper().tolist())

    # Build postcode → state mapping
    postcode_to_state = None
    if state_col:
        postcode_to_state = dict(zip(
            df[code_col].str.upper(),
            df[state_col].str.lower()
        ))

    return valid_postcodes, postcode_to_state

def clean_borough_data(df, valid_boroughs, direction_map, year):
    """Clean Borough level rental data"""
    print(f"  Cleaning Borough data...")

    original_count = len(df)

    # 1. Check required columns
    if 'borough' not in df.columns:
        print(f"    Error: Cannot find borough column")
        return None

    # 2. Remove empty rows
    df = df.dropna(subset=['borough'], how='all')

    # 3. Standardize Borough names
    df['borough'] = df['borough'].astype(str).str.lower().str.strip()
    df['borough'] = df['borough'].replace(BOROUGH_NAME_MAPPING)

    # 4. Filter valid Boroughs
    if valid_boroughs:
        before = len(df)
        df = df[df['borough'].isin(valid_boroughs)]
        print(f"    Borough filter: {before} -> {len(df)}")

    # 5. Standardize Category
    if 'category' in df.columns:
        df['category'] = df['category'].astype(str).str.lower().str.strip()
        df['category'] = df['category'].replace(CATEGORY_MAPPING)

        # Remove Room type
        before = len(df)
        df = df[~df['category'].isin(EXCLUDED_CATEGORIES)]
        print(f"    Remove Room: {before} -> {len(df)}")

    # 6. Convert numeric columns
    numeric_cols = ['count', 'mean', 'median', 'lower_quartile', 'upper_quartile']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 7. Filter Count >= 30
    if 'count' in df.columns:
        before = len(df)
        df = df[df['count'] >= 30]
        print(f"    Count >= 30: {before} -> {len(df)}")

    # 8. Add Direction
    if direction_map:
        df['direction'] = df['borough'].map(direction_map)

    # 9. Arrange output column order
    output_cols = ['year', 'borough', 'category', 'count', 'mean', 'median',
                   'lower_quartile', 'upper_quartile', 'direction']
    output_cols = [c for c in output_cols if c in df.columns]
    df = df[output_cols]

    # 10. Sort
    df = df.sort_values(['borough', 'category']).reset_index(drop=True)

    print(f"    Final: {len(df)} records")

    return df

def clean_postcode_data(df, valid_postcodes, postcode_to_state, year):
    """Clean Postcode level rental data"""
    print(f"  Cleaning Postcode data...")

    original_count = len(df)

    # 1. Check required columns
    if 'postcode' not in df.columns:
        print(f"    Error: Cannot find postcode column")
        return None

    # 2. Remove empty rows
    df = df.dropna(subset=['postcode'], how='all')

    # 3. Standardize Postcode
    df['postcode'] = df['postcode'].astype(str).str.upper().str.strip()

    # 4. Filter valid Postcodes (must be in outward_code_table)
    if valid_postcodes:
        before = len(df)
        df = df[df['postcode'].isin(valid_postcodes)]
        removed = before - len(df)
        print(f"    Filter valid Postcode: {before} -> {len(df)} (removed {removed} not in outward_code_table)")

    # 5. Standardize Category
    if 'category' in df.columns:
        df['category'] = df['category'].astype(str).str.lower().str.strip()
        df['category'] = df['category'].replace(CATEGORY_MAPPING)

        # Remove Room type
        before = len(df)
        df = df[~df['category'].isin(EXCLUDED_CATEGORIES)]
        print(f"    Remove Room: {before} -> {len(df)}")

    # 6. Convert numeric columns
    numeric_cols = ['count', 'mean', 'median', 'lower_quartile', 'upper_quartile']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 7. Filter Count >= 30
    if 'count' in df.columns:
        before = len(df)
        df = df[df['count'] >= 30]
        print(f"    Count >= 30: {before} -> {len(df)}")

    # 8. Add State (inner/outer/border)
    if postcode_to_state:
        df['state'] = df['postcode'].map(postcode_to_state)

    # 9. Arrange output column order
    output_cols = ['year', 'postcode', 'category', 'count', 'mean', 'median',
                   'lower_quartile', 'upper_quartile', 'state']
    output_cols = [c for c in output_cols if c in df.columns]
    df = df[output_cols]

    # 10. Sort
    df = df.sort_values(['postcode', 'category']).reset_index(drop=True)

    print(f"    Final: {len(df)} records")

    return df

# ============================================================================
# Main
# ============================================================================

def main():
    print("="*60)
    print("ONS Private Rental Market in London - Data Cleaning Script v2")
    print("="*60)

    # Load configuration
    config = load_config()
    rent_dir, output_dir, lookup_dir = get_paths(config)

    print(f"\nInput directory: {rent_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Lookup directory: {lookup_dir}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load mapping tables
    valid_boroughs, direction_map = load_borough_mapping(lookup_dir)
    if valid_boroughs:
        print(f"\nValid Borough count: {len(valid_boroughs)}")

    valid_postcodes, postcode_to_state = load_outward_code_mapping(lookup_dir)
    if valid_postcodes:
        print(f"Valid Outward Code count: {len(valid_postcodes)}")

    # Scan rental files (only .xlsx)
    if not os.path.exists(rent_dir):
        print(f"\nError: Rental directory does not exist: {rent_dir}")
        return

    rent_files = []
    pattern = re.compile(r'^rent_(\d{4})\.xlsx$', re.IGNORECASE)

    for filename in os.listdir(rent_dir):
        match = pattern.match(filename)
        if match:
            year = int(match.group(1))
            filepath = os.path.join(rent_dir, filename)
            rent_files.append((year, filepath))

    rent_files.sort(key=lambda x: x[0])

    if not rent_files:
        print(f"\nError: Cannot find rental files (rent_YYYY.xlsx)")
        print(f"Please run download_rent.py first to download data")
        return

    print(f"\nFound {len(rent_files)} rental files")

    # Process each year
    borough_success = 0
    borough_fail = 0
    postcode_success = 0
    postcode_fail = 0

    for year, filepath in rent_files:
        print(f"\n[{year}] Processing {os.path.basename(filepath)}...")

        try:
            excel_file = pd.ExcelFile(filepath)
            available_sheets = excel_file.sheet_names
            print(f"  Available Sheets: {available_sheets}")

            # ============ Process Borough Data ============
            borough_sheet = find_sheet(excel_file, BOROUGH_SHEETS)
            if borough_sheet:
                print(f"  Reading {borough_sheet} (Borough)...")
                df = read_sheet_data(filepath, borough_sheet, 'borough', year)

                if df is not None and len(df) > 0:
                    cleaned_df = clean_borough_data(df, valid_boroughs, direction_map, year)

                    if cleaned_df is not None and len(cleaned_df) > 0:
                        output_path = os.path.join(output_dir, f"rent_{year}_borough.csv")
                        cleaned_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                        print(f"  Borough: {os.path.basename(output_path)}")
                        borough_success += 1
                    else:
                        print(f"  Borough: No data after cleaning")
                        borough_fail += 1
                else:
                    print(f"  Borough: Read failed")
                    borough_fail += 1
            else:
                print(f"  Warning: Cannot find Borough Sheet")
                borough_fail += 1

            # ============ Process Postcode Data ============
            postcode_sheet = find_sheet(excel_file, POSTCODE_SHEETS)
            if postcode_sheet:
                print(f"  Reading {postcode_sheet} (Postcode)...")
                df = read_sheet_data(filepath, postcode_sheet, 'postcode', year)

                if df is not None and len(df) > 0:
                    cleaned_df = clean_postcode_data(df, valid_postcodes, postcode_to_state, year)

                    if cleaned_df is not None and len(cleaned_df) > 0:
                        output_path = os.path.join(output_dir, f"rent_{year}_postcode.csv")
                        cleaned_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                        print(f"  Postcode: {os.path.basename(output_path)}")
                        postcode_success += 1
                    else:
                        print(f"  Postcode: No data after cleaning")
                        postcode_fail += 1
                else:
                    print(f"  Postcode: Read failed")
                    postcode_fail += 1
            else:
                print(f"  Warning: Cannot find Postcode Sheet")
                postcode_fail += 1

        except Exception as e:
            print(f"  Processing failed: {e}")
            borough_fail += 1
            postcode_fail += 1

    # Statistics
    print("\n" + "="*60)
    print("Processing complete:")
    print(f"  Borough:  {borough_success} succeeded, {borough_fail} failed")
    print(f"  Postcode: {postcode_success} succeeded, {postcode_fail} failed")
    print("="*60)

if __name__ == "__main__":
    main()
