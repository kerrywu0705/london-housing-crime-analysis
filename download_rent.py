"""
ONS Private Rental Market in London Downloader
Data source: ONS Ad-hoc data (Calendar year version Jan-Dec)
Features: Download 2019-2024 data, convert to xlsx format, auto-clean header/footer notes
"""

import os
import re
import time
import argparse
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ============================================================================
# Configuration
# ============================================================================

OUTPUT_DIR = r"C:\Users\kerry\Desktop\london_property\property_rent"
BASE_URL = "https://www.ons.gov.uk"

# Known page URLs (Calendar year version Jan-Dec)
KNOWN_PAGES = {
    2019: "/peoplepopulationandcommunity/housing/adhocs/11100privaterentalmarketinlondonjanuary2019todecember2019",
    2020: "/peoplepopulationandcommunity/housing/adhocs/12871privaterentalmarketinlondonjanuarytodecember2020",
    2021: "/peoplepopulationandcommunity/housing/adhocs/14323privaterentalmarketinlondonjanuary2021todecember2021",
    2022: "/peoplepopulationandcommunity/housing/adhocs/1024privaterentalmarketinlondonjanuary2022todecember2022",
    2023: "/economy/inflationandpriceindices/adhocs/1830privaterentalmarketinlondonjanuary2023todecember2023",
    2024: "/economy/inflationandpriceindices/adhocs/1806privaterentalmarketinlondonjanuary2024todecember2024",
}

# Valid Borough list (33 + City of London, lowercase, including common variants)
VALID_BOROUGHS = {
    'barking and dagenham', 'barking & dagenham',
    'barnet',
    'bexley',
    'brent',
    'bromley',
    'camden',
    'city of london',
    'city of westminster', 'westminster',
    'croydon',
    'ealing',
    'enfield',
    'greenwich',
    'hackney',
    'hammersmith and fulham', 'hammersmith & fulham',
    'haringey',
    'harrow',
    'havering',
    'hillingdon',
    'hounslow',
    'islington',
    'kensington and chelsea', 'kensington & chelsea',
    'kingston upon thames',
    'lambeth',
    'lewisham',
    'merton',
    'newham',
    'redbridge',
    'richmond upon thames',
    'southwark',
    'sutton',
    'tower hamlets',
    'waltham forest',
    'wandsworth',
}

# Postcode District regex pattern (e.g., E1, SW1, N10, EC1A)
POSTCODE_PATTERN = re.compile(r'^[A-Z]{1,2}[0-9]{1,2}[A-Z]?$', re.IGNORECASE)

# ============================================================================
# Excel Cleaning Functions
# ============================================================================

def find_header_row(df, keyword):
    """Find the header row containing keyword (check all columns)"""
    keyword_lower = keyword.lower().strip()

    for idx in range(len(df)):
        row = df.iloc[idx]
        for col_idx, cell in enumerate(row):
            if pd.notna(cell):
                cell_str = str(cell).lower().strip()
                if cell_str == keyword_lower:
                    return idx, col_idx  # Return row number and column index

    return None, None


def is_valid_borough(value):
    """Check if value is a valid Borough"""
    if pd.isna(value):
        return False
    val_str = str(value).lower().strip()
    return val_str in VALID_BOROUGHS


def is_valid_postcode(value):
    """Check if value is a valid Postcode District"""
    if pd.isna(value):
        return False
    val_str = str(value).strip()
    return bool(POSTCODE_PATTERN.match(val_str))


def clean_sheet(df, sheet_type):
    """
    Clean a single sheet
    sheet_type: 'borough' or 'postcode'
    """
    # 1. Determine header keyword and validation function
    if sheet_type == 'borough':
        header_keyword = 'Borough'
        is_valid_row = is_valid_borough
    else:  # postcode
        header_keyword = 'Postcode District'
        is_valid_row = is_valid_postcode

    # 2. Find header row
    header_row, key_col = find_header_row(df, header_keyword)

    if header_row is None:
        print(f"      Cannot find header '{header_keyword}'")
        return None

    print(f"      Found header at row {header_row + 1}, column {key_col + 1}")

    # 3. Set header and get data below
    new_header = df.iloc[header_row].values
    data_df = df.iloc[header_row + 1:].copy()
    data_df.columns = new_header
    data_df = data_df.reset_index(drop=True)

    # 4. Remove leading empty columns (if key_col > 0, there are empty columns before)
    first_valid_col = 0
    for i, col in enumerate(data_df.columns):
        if pd.notna(col) and str(col).strip():
            first_valid_col = i
            break

    if first_valid_col > 0:
        data_df = data_df.iloc[:, first_valid_col:]
        print(f"      Removed first {first_valid_col} empty columns")

    # 5. Remove trailing notes (stop at first invalid row)
    valid_count = 0
    for idx in range(len(data_df)):
        first_cell = data_df.iloc[idx, 0]
        if is_valid_row(first_cell):
            valid_count += 1
        else:
            break

    # Keep only valid data
    data_df = data_df.iloc[:valid_count]

    # 6. Remove completely empty rows and columns
    data_df = data_df.dropna(how='all')
    data_df = data_df.dropna(axis=1, how='all')

    print(f"      Kept {len(data_df)} records")

    return data_df


def clean_and_convert_excel(input_path, output_path):
    """Clean Excel file, keep only Table 1.2 and Table 1.3"""
    excel_file = None
    try:
        # Read original Excel
        excel_file = pd.ExcelFile(input_path)
        original_sheets = excel_file.sheet_names

        print(f"  Original Sheets: {original_sheets}")

        # Determine sheet name format (2019-2022 vs 2023+)
        if 'Table 1.2' in original_sheets:
            borough_sheet = 'Table 1.2'
            postcode_sheet = 'Table 1.3'
        elif '2' in original_sheets:
            borough_sheet = '2'
            postcode_sheet = '3'
        else:
            print(f"  Warning: Cannot find expected sheets")
            excel_file.close()
            return False

        cleaned_sheets = {}

        # Process Borough sheet (Table 1.2 or 2)
        if borough_sheet in original_sheets:
            print(f"  Processing {borough_sheet}...")
            df = pd.read_excel(excel_file, sheet_name=borough_sheet, header=None)
            cleaned_df = clean_sheet(df, 'borough')
            if cleaned_df is not None and len(cleaned_df) > 0:
                cleaned_sheets['Table 1.2'] = cleaned_df

        # Process Postcode sheet (Table 1.3 or 3)
        if postcode_sheet in original_sheets:
            print(f"  Processing {postcode_sheet}...")
            df = pd.read_excel(excel_file, sheet_name=postcode_sheet, header=None)
            cleaned_df = clean_sheet(df, 'postcode')
            if cleaned_df is not None and len(cleaned_df) > 0:
                cleaned_sheets['Table 1.3'] = cleaned_df

        # Close original file
        excel_file.close()
        excel_file = None

        if not cleaned_sheets:
            print(f"  Error: No sheets were successfully cleaned")
            return False

        # Write to new xlsx file
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet_name, df in cleaned_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        print(f"  Output: {os.path.basename(output_path)}")
        print(f"     Sheets: {list(cleaned_sheets.keys())}")

        return True

    except Exception as e:
        print(f"  Cleaning failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Ensure file is closed
        if excel_file is not None:
            try:
                excel_file.close()
            except:
                pass


# ============================================================================
# Download Functions
# ============================================================================

def get_download_url_from_page(page_url):
    """Parse actual download link from ONS page"""
    full_url = BASE_URL + page_url if page_url.startswith('/') else page_url

    try:
        response = requests.get(full_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find .xls or .xlsx download link
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/file?uri=' in href and ('.xls' in href.lower()):
                download_url = BASE_URL + href if href.startswith('/') else href
                # Determine file format
                file_ext = '.xlsx' if '.xlsx' in href.lower() else '.xls'
                return download_url, file_ext

        return None, None

    except requests.exceptions.RequestException as e:
        print(f"  Failed to parse page: {e}")
        return None, None


def search_new_years():
    """Search ONS website for new years of data"""
    print("Searching ONS website for new years...")

    search_url = "https://www.ons.gov.uk/search?q=Private+rental+market+in+London+January+December"

    try:
        response = requests.get(search_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        found_years = {}

        pattern = re.compile(r'privaterentalmarketinlondonjanuary(\d{4})todecember\1', re.IGNORECASE)

        for link in soup.find_all('a', href=True):
            href = link['href']
            match = pattern.search(href)
            if match:
                year = int(match.group(1))
                if year not in KNOWN_PAGES and year not in found_years:
                    found_years[year] = href
                    print(f"  Found new year: {year}")

        return found_years

    except requests.exceptions.RequestException as e:
        print(f"  Search failed: {e}")
        return {}


def get_all_available_years():
    """Get all available years"""
    all_years = dict(KNOWN_PAGES)
    new_years = search_new_years()
    all_years.update(new_years)
    return all_years


def list_available_years():
    """List all available years"""
    print("\nChecking available years...")
    all_years = get_all_available_years()

    print("\n" + "="*50)
    print("Available Rental Data Years (Calendar Year Version)")
    print("="*50)

    for year in sorted(all_years.keys()):
        source = "Known" if year in KNOWN_PAGES else "New"
        print(f"  {year} ({source})")

    print("="*50)
    print(f"Total {len(all_years)} years")


def check_file_exists(filepath):
    """Check if file exists"""
    if os.path.exists(filepath):
        filename = os.path.basename(filepath)
        response = input(f"File {filename} already exists. Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print(f"  Skipped")
            return False
        else:
            os.remove(filepath)
    return True


def download_file(url, filepath):
    """Download file"""
    print(f"  Downloading...")

    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)

        size_kb = len(response.content) / 1024
        print(f"  Download complete: {os.path.basename(filepath)} ({size_kb:.1f} KB)")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  Download failed: {e}")
        return False


def download_year(year, all_years=None):
    """Download and clean data for specified year"""
    if all_years is None:
        all_years = get_all_available_years()

    if year not in all_years:
        print(f"Error: Cannot find data for year {year}")
        return False

    print(f"\n[{year}] Processing...")

    # Get page URL
    page_url = all_years[year]

    # Parse download link from page
    print(f"  Parsing page...")
    download_url, file_ext = get_download_url_from_page(page_url)

    if not download_url:
        print(f"  Error: Cannot find download link")
        return False

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Final output path (unified to .xlsx)
    output_path = os.path.join(OUTPUT_DIR, f"rent_{year}.xlsx")

    # Check if already exists
    if not check_file_exists(output_path):
        return False

    # Download to temp file
    temp_path = os.path.join(OUTPUT_DIR, f"temp_{year}{file_ext}")

    if not download_file(download_url, temp_path):
        return False

    # Clean and convert
    print(f"  Cleaning Excel...")
    success = clean_and_convert_excel(temp_path, output_path)

    # Delete temp file (with retry mechanism for Windows file locking)
    if os.path.exists(temp_path):
        for attempt in range(3):
            try:
                time.sleep(0.5)  # Wait for file release
                os.remove(temp_path)
                break
            except PermissionError:
                if attempt < 2:
                    print(f"  Waiting for file release... (attempt {attempt + 2}/3)")
                    time.sleep(1)
                else:
                    print(f"  Warning: Cannot delete temp file {temp_path}")
            except Exception as e:
                print(f"  Warning: Failed to delete temp file: {e}")
                break

    if success:
        print(f"  {year} completed successfully")
    else:
        print(f"  {year} processing failed")

    return success


def download_range(start_year, end_year):
    """Download specified year range"""
    print(f"\nDownloading {start_year}-{end_year} data")

    all_years = get_all_available_years()

    success_count = 0
    fail_count = 0

    for year in range(start_year, end_year + 1):
        if year in all_years:
            if download_year(year, all_years):
                success_count += 1
            else:
                fail_count += 1
        else:
            print(f"\n[{year}] Data not found, skipped")
            fail_count += 1

    print("\n" + "="*50)
    print(f"Download complete: {success_count} succeeded, {fail_count} failed")
    print("="*50)


def download_all():
    """Download all available years"""
    print("\nDownloading all available years")

    all_years = get_all_available_years()
    years = sorted(all_years.keys())

    if not years:
        print("Error: No available years found")
        return

    print(f"Found {len(years)} years: {years[0]}-{years[-1]}")

    success_count = 0
    fail_count = 0

    for year in years:
        if download_year(year, all_years):
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "="*50)
    print(f"Download complete: {success_count} succeeded, {fail_count} failed")
    print("="*50)


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ONS Private Rental Market in London Downloader',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--list', action='store_true',
                        help='List all available years')
    parser.add_argument('--year', type=int,
                        help='Download specified year (e.g., --year 2024)')
    parser.add_argument('--range', type=int, nargs=2, metavar=('START', 'END'),
                        help='Download year range (e.g., --range 2019 2024)')
    parser.add_argument('--all', action='store_true',
                        help='Download all available years')
    parser.add_argument('--search', action='store_true',
                        help='Search for new years')

    args = parser.parse_args()

    print("="*60)
    print("ONS Private Rental Market in London Downloader")
    print("="*60)

    if args.list:
        list_available_years()
        return

    if args.search:
        new_years = search_new_years()
        if new_years:
            print(f"\nFound {len(new_years)} new years:")
            for year in sorted(new_years.keys()):
                print(f"  {year}")
        else:
            print("\nNo new years found")
        return

    if args.year:
        download_year(args.year)
        return

    if args.range:
        download_range(args.range[0], args.range[1])
        return

    if args.all:
        download_all()
        return

    # Show help if no arguments
    parser.print_help()
    print("\n" + "="*60)
    print("Examples:")
    print("  python download_rent.py --list           # List available years")
    print("  python download_rent.py --year 2024      # Download 2024")
    print("  python download_rent.py --range 2019 2024  # Download 2019-2024")
    print("  python download_rent.py --all            # Download all")
    print("  python download_rent.py --search         # Search for new years")
    print("="*60)


if __name__ == "__main__":
    main()
