"""
London Property Price - Data Cleaning Script v3
Features: Scan folder, import to MySQL, filter London data, build global mapping table, export raw transaction CSV
New: Build global Outward Code mapping table
Output: price_YYYY_filtered.csv (raw transaction records, not aggregated, includes state field)
"""

import os
import re
import configparser
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np

# ============================================================================
# Configuration
# ============================================================================

# Property type mapping
PROPERTY_TYPE_MAP = {
    'D': 'detached',       # Detached house
    'S': 'semi_detached',  # Semi-detached house
    'T': 'terraced',       # Terraced house
    'F': 'flat',           # Flat/Maisonette
    'O': 'other'           # Other
}

# Output path (hardcoded)
OUTPUT_DIR = r'C:\Users\kerry\Desktop\london_property\property_price_filtered'

# ============================================================================
# Load Configuration
# ============================================================================

def load_config(config_path='config.ini'):
    """Load configuration file"""
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')
    return config

# ============================================================================
# MySQL Connection
# ============================================================================

def get_connection(config):
    """Establish MySQL connection"""
    try:
        conn = mysql.connector.connect(
            host=config['mysql']['host'],
            port=int(config['mysql']['port']),
            user=config['mysql']['user'],
            password=config['mysql']['password'],
            database=config['mysql']['database'],
            allow_local_infile=True
        )
        return conn
    except Error as e:
        print(f"Connection failed: {e}")
        return None

# ============================================================================
# File Scanning
# ============================================================================

def scan_csv_files(directory):
    """Scan folder for pp-YYYY.csv files, return list of years"""
    years = []
    pattern = re.compile(r'^pp-(\d{4})\.csv$', re.IGNORECASE)

    if not os.path.exists(directory):
        print(f"Directory does not exist: {directory}")
        return years

    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            year = int(match.group(1))
            years.append(year)

    return sorted(years)

def get_existing_filtered_files(output_dir):
    """Get existing price_YYYY_filtered.csv files"""
    existing_years = []
    pattern = re.compile(r'^price_(\d{4})_filtered\.csv$')

    if not os.path.exists(output_dir):
        return existing_years

    for filename in os.listdir(output_dir):
        match = pattern.match(filename)
        if match:
            existing_years.append(int(match.group(1)))

    return existing_years

# ============================================================================
# Create Lookup Tables
# ============================================================================

def ensure_lookup_tables(conn, lookup_dir):
    """Ensure lookup tables exist, create if not"""
    cursor = conn.cursor()

    # Check if borough_mapping exists
    cursor.execute("SHOW TABLES LIKE 'borough_mapping'")
    if not cursor.fetchone():
        print("Creating borough_mapping table...")
        create_borough_mapping(conn, lookup_dir)
    else:
        print("borough_mapping table already exists")

    # Check if outward_code exists
    cursor.execute("SHOW TABLES LIKE 'outward_code'")
    if not cursor.fetchone():
        print("Creating outward_code table...")
        create_outward_code(conn, lookup_dir)
    else:
        print("outward_code table already exists")

    cursor.close()

def create_borough_mapping(conn, lookup_dir):
    """Create borough_mapping table"""
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS `borough_mapping`")
    cursor.execute("""
        CREATE TABLE `borough_mapping` (
            `id` VARCHAR(20),
            `borough` VARCHAR(100),
            `direction` VARCHAR(20),
            PRIMARY KEY (`borough`)
        )
    """)

    csv_path = os.path.join(lookup_dir, 'borough_mapping.csv').replace('\\', '/')
    cursor.execute(f"""
        LOAD DATA LOCAL INFILE '{csv_path}'
        INTO TABLE `borough_mapping`
        FIELDS TERMINATED BY ','
        ENCLOSED BY '"'
        LINES TERMINATED BY '\\r\\n'
        IGNORE 1 LINES
    """)

    conn.commit()
    cursor.close()
    print(f"borough_mapping created successfully")

def create_outward_code(conn, lookup_dir):
    """Create outward_code table"""
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS `outward_code`")
    cursor.execute("""
        CREATE TABLE `outward_code` (
            `outward_code` VARCHAR(10),
            `state` VARCHAR(20),
            PRIMARY KEY (`outward_code`)
        )
    """)

    csv_path = os.path.join(lookup_dir, 'outward_code_table.csv').replace('\\', '/')
    cursor.execute(f"""
        LOAD DATA LOCAL INFILE '{csv_path}'
        INTO TABLE `outward_code`
        FIELDS TERMINATED BY ','
        ENCLOSED BY '"'
        LINES TERMINATED BY '\\r\\n'
        IGNORE 1 LINES
    """)

    conn.commit()
    cursor.close()
    print(f"outward_code created successfully")

# ============================================================================
# Build Global Reference Table
# ============================================================================

def build_global_reference_table(conn, filtered_years, lookup_dir):
    """Build Outward Code mapping table using all years data"""
    print(f"\n{'='*50}")
    print(f"Building Global Reference Table")
    print('='*50)

    # Load the mapping table
    outward_code = pd.read_csv(
        os.path.join(lookup_dir, 'outward_code_table.csv'),
        encoding='utf-8'
    )
    # Clean possible carriage return characters
    outward_code['state'] = outward_code['state'].str.strip()

    # Merge all years data
    print("[1/4] Merging all years data...")
    all_data = []

    for year in filtered_years:
        query = f"""
            SELECT
                f.Borough AS borough,
                f.`Town/City` AS town_city,
                f.`Outward Code` AS outward_code,
                f.County AS county
            FROM `{year}_london_filtered` AS f
            WHERE f.Price IS NOT NULL
              AND f.Price > 10000
              AND f.Price < 20000000
        """
        df_year = pd.read_sql(query, conn)
        all_data.append(df_year)
        print(f"    {year}: {len(df_year):,} records")

    london_property = pd.concat(all_data, ignore_index=True)
    print(f"    Total: {len(london_property):,} records")

    # Select all rows where Outward Code is not null
    print("[2/4] Building Borough + Town/City -> Outward Code mapping...")
    exist_postcode = london_property[~london_property['outward_code'].isna()]
    print(f"    Records with Outward Code: {len(exist_postcode):,}")

    # Group by Borough and Town/City, get the Outward Code; if multiple exist, select the most frequent one (mode)
    temp_ref = exist_postcode.groupby(['borough', 'town_city'])['outward_code'].agg(
        lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else None
    ).reset_index()

    # Merge two tables
    temp_ref = temp_ref.merge(outward_code, left_on='outward_code', right_on='outward_code', how='left')

    print(f"    Mapping table records: {len(temp_ref)}")
    print(f"    Missing state count: {temp_ref['state'].isna().sum()}")

    # Build Outward Code -> Borough mapping dictionary (for handling source_flag='p' records)
    print("[3/4] Building Outward Code -> Borough mapping dictionary...")
    outward_code_list = london_property[london_property['county'] == 'greater london']
    outward_code_list = outward_code_list.drop_duplicates(subset=['borough', 'outward_code']).reset_index(drop=True)
    code_to_borough = dict(zip(outward_code_list['outward_code'], outward_code_list['borough']))
    print(f"    Outward Code -> Borough mapping: {len(code_to_borough)} records")

    print("[4/4] Global reference table completed")

    return {
        'outward_code_ref': temp_ref,
        'code_to_borough': code_to_borough
    }

# ============================================================================
# Export Raw Transactions (No Aggregation)
# ============================================================================

def export_raw_transactions(conn, year, filtered_table, output_dir, global_ref):
    """Read data from MySQL, use global mapping table to fill missing values, export raw transaction CSV"""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"price_{year}_filtered.csv")

    print(f"\n{'='*50}")
    print(f"[Phase 3] Exporting {year} data")
    print('='*50)

    # Unpack global reference table
    outward_code_ref = global_ref['outward_code_ref']
    code_to_borough = global_ref['code_to_borough']

    # Read filtered data (include Town/City field for backfilling)
    print(f"[1/6] Reading data...")
    query = f"""
        SELECT
            f.`Transaction unique identifier` AS transaction_id,
            f.Price AS price,
            f.`Date of Transfer` AS date_of_transfer,
            f.Postcode AS postcode,
            f.`Outward Code` AS outward_code,
            f.`Property Type` AS property_type,
            f.`Old/New` AS status,
            f.Duration AS duration,
            f.`Town/City` AS town_city,
            f.Borough AS borough,
            f.County AS county,
            f.state,
            f.source_flag
        FROM `{filtered_table}` AS f
        WHERE f.Borough IS NOT NULL
          AND f.Price IS NOT NULL
          AND f.Price > 10000
          AND f.Price < 20000000
          AND f.`Property Type` <> 'O'
    """

    df = pd.read_sql(query, conn)
    print(f"    Read {len(df):,} valid records")

    if len(df) == 0:
        print("    Warning: No valid data, skipping")
        return None

    # Count missing values before backfilling
    missing_before = {
        'postcode': df['postcode'].isna().sum(),
        'outward_code': df['outward_code'].isna().sum(),
        'state': df['state'].isna().sum()
    }
    print(f"    Missing before backfill: postcode={missing_before['postcode']}, outward_code={missing_before['outward_code']}, state={missing_before['state']}")

    # ========================================================================
    # [2/6] Use global mapping table to backfill missing values
    # ========================================================================
    print(f"[2/6] Using global mapping table to backfill missing values...")

    # Merge with global reference table
    df = df.merge(outward_code_ref, on=['borough', 'town_city'], how='left', suffixes=['', '_ref'])

    # Fill in missing Postcode values
    df['postcode'] = df['postcode'].fillna(df['outward_code_ref'])

    # Fill in missing Outward Code values
    df['outward_code'] = df['outward_code'].fillna(df['outward_code_ref'])

    # Fill in missing state values
    df['state'] = df['state'].fillna(df['state_ref'])

    # Drop duplicate columns
    df = df.drop(['outward_code_ref', 'state_ref'], axis=1)

    # Count missing values after backfilling
    missing_after = {
        'postcode': df['postcode'].isna().sum(),
        'outward_code': df['outward_code'].isna().sum(),
        'state': df['state'].isna().sum()
    }
    print(f"    Missing after backfill: postcode={missing_after['postcode']}, outward_code={missing_after['outward_code']}, state={missing_after['state']}")

    # ========================================================================
    # [3/6] Handle source_flag='p' records
    # ========================================================================
    print(f"[3/6] Handling source_flag='p' records...")

    # Select rows where source_flag is 'p' and state is 'inner'
    inner = df[(df['source_flag'] == 'p') & (df['state'] == 'inner')]

    # Select rows where source_flag is 'p' and state is 'border'
    border = df[(df['source_flag'] == 'p') & (df['state'] == 'border')]

    print(f"    source_flag='p' and state='inner': {len(inner):,} records")
    print(f"    source_flag='p' and state='border': {len(border):,} records")
    print(f"    Using global Outward Code -> Borough mapping: {len(code_to_borough)} records")

    # For records with state 'inner', set county to 'greater london'
    df.loc[inner.index, 'county'] = 'greater london'

    # For records with state 'inner', update borough using the global mapping dictionary
    df.loc[inner.index, 'borough'] = df.loc[inner.index, 'outward_code'].map(code_to_borough)

    # For records with state 'border', remove those not located in Greater London
    df = df.drop(index=border.index)

    print(f"    Records remaining after removing border: {len(df):,}")

    # ========================================================================
    # [4/6] Standardize fields
    # ========================================================================
    print(f"[4/6] Standardizing fields...")

    # Process date field, extract year and month
    df['date_of_transfer'] = pd.to_datetime(df['date_of_transfer'], errors='coerce')
    df['year'] = df['date_of_transfer'].dt.year
    df['month'] = df['date_of_transfer'].dt.month
    df['date_of_transfer'] = df['date_of_transfer'].dt.strftime('%Y-%m-%d')

    # Standardize text fields
    df['borough'] = df['borough'].str.lower().str.strip()
    df['county'] = df['county'].str.lower().str.strip()
    df['property_type'] = df['property_type'].str.upper().str.strip()
    df['status'] = df['status'].str.upper().str.strip()
    df['duration'] = df['duration'].str.upper().str.strip()

    # ========================================================================
    # [5/6] Map direction
    # ========================================================================
    print(f"[5/6] Mapping direction...")

    # Read borough_mapping to build direction mapping
    borough_mapping = pd.read_sql("SELECT borough, direction FROM borough_mapping", conn)
    direction_borough = dict(zip(borough_mapping['borough'], borough_mapping['direction']))

    # Map direction data
    df['direction'] = df['borough'].map(direction_borough)

    print(f"    Missing direction count: {df['direction'].isna().sum()}")

    # Reorder columns (remove town_city, keep state, source_flag, direction)
    df = df[['transaction_id', 'price', 'date_of_transfer', 'year', 'month',
             'postcode', 'outward_code', 'property_type', 'status', 'duration',
             'borough', 'direction', 'county', 'state', 'source_flag']]

    # ========================================================================
    # [6/6] Export
    # ========================================================================
    print(f"[6/6] Exporting CSV: {output_path}...")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"    Exported {len(df):,} raw transaction records")
    print(f"    Borough count: {df['borough'].nunique()}")
    print(f"    Property Type distribution: {df['property_type'].value_counts().to_dict()}")
    print(f"    Year range: {df['year'].min()} - {df['year'].max()}")
    print(f"    State distribution: {df['state'].value_counts().to_dict()}")
    print(f"    Source Flag distribution: {df['source_flag'].value_counts().to_dict()}")

    return output_path

# ============================================================================
# Import and Clean Annual Data (Import Only, No Export)
# ============================================================================

def import_year_to_mysql(conn, year, csv_dir):
    """Import and clean specified year data to MySQL (no export)"""
    print(f"\n{'='*50}")
    print(f"[Phase 1] Importing {year} data to MySQL")
    print('='*50)

    cursor = conn.cursor()
    csv_path = os.path.join(csv_dir, f'pp-{year}.csv').replace('\\', '/')

    raw_table = f"{year}_raw"
    filtered_table = f"{year}_london_filtered"

    try:
        # 1. Create raw table
        print(f"[1/8] Creating {raw_table} table...")
        cursor.execute(f"DROP TABLE IF EXISTS `{raw_table}`")
        cursor.execute(f"""
            CREATE TABLE `{raw_table}` (
                `Transaction unique identifier` VARCHAR(255),
                `Price` INT,
                `Date of Transfer` VARCHAR(20),
                `Postcode` VARCHAR(20),
                `Property Type` VARCHAR(10),
                `Old/New` VARCHAR(10),
                `Duration` VARCHAR(10),
                `PAON` VARCHAR(255),
                `SAON` VARCHAR(255),
                `Street` VARCHAR(255),
                `Locality` VARCHAR(255),
                `Town/City` VARCHAR(255),
                `Borough` VARCHAR(255),
                `County` VARCHAR(255),
                `PPD Category Type` VARCHAR(50),
                `Record Status` VARCHAR(10)
            )
        """)

        # 2. Import CSV
        print(f"[2/8] Importing CSV: {csv_path}...")
        cursor.execute(f"""
            LOAD DATA LOCAL INFILE '{csv_path}'
            INTO TABLE `{raw_table}`
            FIELDS TERMINATED BY ','
            ENCLOSED BY '"'
            LINES TERMINATED BY '\\r\\n'
        """)
        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM `{raw_table}`")
        raw_count = cursor.fetchone()[0]
        print(f"    Imported {raw_count:,} records")

        # 3. Drop unnecessary columns
        print(f"[3/8] Dropping unnecessary columns...")
        for col in ['PAON', 'SAON', 'Street', 'Locality', 'PPD Category Type', 'Record Status']:
            cursor.execute(f"ALTER TABLE `{raw_table}` DROP COLUMN `{col}`")
        conn.commit()

        # 4. Standardize text fields
        print(f"[4/8] Standardizing text fields...")
        cursor.execute(f"""
            UPDATE `{raw_table}`
            SET
                `County` = LOWER(TRIM(`County`)),
                `Borough` = LOWER(TRIM(`Borough`)),
                `Town/City` = LOWER(TRIM(`Town/City`))
        """)

        cursor.execute(f"""
            UPDATE `{raw_table}`
            SET `Borough` = 'westminster'
            WHERE `Borough` = 'city of westminster'
        """)
        conn.commit()

        # 5. Create Outward Code field
        print(f"[5/8] Creating Outward Code field...")
        cursor.execute(f"ALTER TABLE `{raw_table}` ADD COLUMN `Outward Code` VARCHAR(10)")
        cursor.execute(f"""
            UPDATE `{raw_table}`
            SET `Outward Code` = TRIM(SUBSTRING(`Postcode`, 1, INSTR(`Postcode`, ' ') - 1))
            WHERE `Postcode` IS NOT NULL AND INSTR(`Postcode`, ' ') > 0
        """)
        conn.commit()

        # 6. Filter London data
        print(f"[6/8] Filtering London data...")
        cursor.execute(f"DROP TABLE IF EXISTS `{filtered_table}`")
        cursor.execute(f"""
            CREATE TABLE `{filtered_table}` AS
            SELECT
                raw.*,
                oc.state,
                (CASE
                    WHEN (raw.County = 'greater london') AND (bm.borough IS NOT NULL) AND (oc.outward_code IS NOT NULL) THEN 'cbp'
                    WHEN (raw.County = 'greater london') AND (bm.borough IS NOT NULL) THEN 'cb'
                    WHEN (raw.County = 'greater london') AND (oc.outward_code IS NOT NULL) THEN 'cp'
                    WHEN (bm.borough IS NOT NULL) AND (oc.outward_code IS NOT NULL) THEN 'bp'
                    WHEN (raw.County = 'greater london') THEN 'c'
                    WHEN (bm.borough IS NOT NULL) THEN 'b'
                    WHEN (oc.outward_code IS NOT NULL) THEN 'p'
                    ELSE 'null'
                END) AS source_flag
            FROM `{raw_table}` AS raw
            LEFT JOIN `borough_mapping` AS bm
                ON raw.Borough = bm.borough
            LEFT JOIN `outward_code` AS oc
                ON raw.`Outward Code` = oc.outward_code
            WHERE
                raw.County = 'greater london'
                OR bm.borough IS NOT NULL
                OR oc.outward_code IS NOT NULL
        """)
        conn.commit()

        # 7. Clean anomalous data
        print(f"[7/8] Cleaning anomalous data...")
        cursor.execute(f"""
            DELETE FROM `{filtered_table}`
            WHERE source_flag = 'cb' AND `Outward Code` IS NOT NULL AND `Outward Code` <> ''
        """)
        cursor.execute(f"""
            DELETE FROM `{filtered_table}`
            WHERE source_flag = 'p' AND state = 'outer'
        """)
        conn.commit()

        # 8. Statistics
        print(f"[8/8] Filtering statistics...")
        cursor.execute(f"SELECT COUNT(*) FROM `{filtered_table}`")
        filtered_count = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT source_flag, COUNT(*) as cnt
            FROM `{filtered_table}`
            GROUP BY source_flag
            ORDER BY cnt DESC
        """)
        source_flags = cursor.fetchall()

        print(f"    Raw records: {raw_count:,}")
        print(f"    London records: {filtered_count:,}")
        print(f"    Source Flag distribution:")
        for flag, cnt in source_flags:
            print(f"      {flag}: {cnt:,}")

        cursor.close()
        print(f"{year} import completed")

        return True

    except Error as e:
        print(f"Error processing {year}: {e}")
        conn.rollback()
        cursor.close()
        return False

# ============================================================================
# Main
# ============================================================================

def main():
    print("="*60)
    print("London Property Price - Data Cleaning Script v3")
    print("="*60)

    # Load configuration
    config = load_config()
    csv_dir = config['paths']['property_price_dir']
    lookup_dir = config['paths']['lookup_table_dir']
    output_dir = OUTPUT_DIR  # Use hardcoded path

    print(f"\nInput directory: {csv_dir}")
    print(f"Output directory: {output_dir}")

    # Connect to MySQL
    print("\nConnecting to MySQL...")
    conn = get_connection(config)
    if not conn:
        return
    print("Connection successful!")

    try:
        # Ensure lookup tables exist
        print("\nChecking lookup tables...")
        ensure_lookup_tables(conn, lookup_dir)

        # Scan CSV files
        print(f"\nScanning directory: {csv_dir}")
        csv_years = scan_csv_files(csv_dir)
        print(f"Found CSV years: {csv_years}")

        if not csv_years:
            print("No CSV files found")
            return

        # ====================================================================
        # Phase 1: Import all years to MySQL
        # ====================================================================
        print("\n" + "="*60)
        print("Phase 1: Import all years to MySQL")
        print("="*60)

        filtered_years = []
        for year in csv_years:
            result = import_year_to_mysql(conn, year, csv_dir)
            if result:
                filtered_years.append(year)

        if not filtered_years:
            print("No years imported successfully")
            return

        # ====================================================================
        # Phase 2: Build global reference table
        # ====================================================================
        global_ref = build_global_reference_table(conn, filtered_years, lookup_dir)

        # ====================================================================
        # Phase 3: Export all years
        # ====================================================================
        print("\n" + "="*60)
        print("Phase 3: Export all years")
        print("="*60)

        for year in filtered_years:
            filtered_table = f"{year}_london_filtered"
            export_raw_transactions(conn, year, filtered_table, output_dir, global_ref)

        # Final statistics
        print("\n" + "="*60)
        print("All processed years:")
        final_years = get_existing_filtered_files(output_dir)
        for year in sorted(final_years):
            csv_path = os.path.join(output_dir, f"price_{year}_filtered.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                print(f"  {year}: {len(df):,} transaction records | Borough: {df['borough'].nunique()} | Property Types: {df['property_type'].nunique()}")
        print("="*60)

        # ====================================================================
        # Phase 4: Clean up MySQL tables
        # ====================================================================
        print("\n" + "="*60)
        print("Phase 4: Clean up MySQL tables")
        print("="*60)

        cursor = conn.cursor()

        # Drop year-related tables
        for year in filtered_years:
            raw_table = f"{year}_raw"
            filtered_table = f"{year}_london_filtered"
            cursor.execute(f"DROP TABLE IF EXISTS `{raw_table}`")
            cursor.execute(f"DROP TABLE IF EXISTS `{filtered_table}`")
            print(f"  Dropped: {raw_table}, {filtered_table}")

        # Drop lookup tables
        cursor.execute("DROP TABLE IF EXISTS `borough_mapping`")
        cursor.execute("DROP TABLE IF EXISTS `outward_code`")
        print("  Dropped: borough_mapping, outward_code")

        conn.commit()
        cursor.close()
        print("MySQL table cleanup completed")

    finally:
        conn.close()
        print("\nConnection closed")

if __name__ == "__main__":
    main()
