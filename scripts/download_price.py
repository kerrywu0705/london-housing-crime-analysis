"""
Land Registry Property Price Data Downloader
Downloads property transaction data from UK Land Registry public dataset.
"""

import os
import argparse
import requests

# ============================================================================
# Configuration
# ============================================================================

OUTPUT_DIR = r"C:\Users\kerry\Desktop\london_property\property_price"
BASE_URL = "http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com"

# CSV Header (Land Registry format)
CSV_HEADER = "Transaction unique identifier,Price,Date of Transfer,Postcode,Property Type,Old/New,Duration,PAON,SAON,Street,Locality,Town/City,Borough,County,PPD Category Type,Record Status"

# ============================================================================
# Functions
# ============================================================================

def get_yearly_url(year):
    """Get the URL for yearly data"""
    return f"{BASE_URL}/pp-{year}.csv"


def check_file_exists(filepath):
    """Check if file exists, ask user whether to overwrite"""
    if os.path.exists(filepath):
        filename = os.path.basename(filepath)
        response = input(f"File {filename} already exists. Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print(f"Skipped {filename}")
            return False
    return True


def download_file(url, filepath):
    """Download file and add header"""
    filename = os.path.basename(filepath)

    # Check if file exists
    if not check_file_exists(filepath):
        return False

    print(f"Downloading {filename}...")

    try:
        response = requests.get(url, timeout=300)
        response.raise_for_status()

        # Add header to the first line of the file
        content = CSV_HEADER + "\n" + response.content.decode('utf-8')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        size_mb = len(response.content) / (1024 * 1024)
        print(f"Download complete: {filepath} ({size_mb:.1f} MB)")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Download failed: {e}")
        return False


def download_years(years):
    """Download data for specified years"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for year in years:
        url = get_yearly_url(year)
        filepath = os.path.join(OUTPUT_DIR, f"pp-{year}.csv")
        download_file(url, filepath)


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Land Registry Property Price Data Downloader')
    parser.add_argument('--year', type=int, help='Download single year (e.g., --year 2024)')
    parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'),
                        help='Download year range (e.g., --range 2020 2024)')

    args = parser.parse_args()

    if not args.year and not args.range:
        parser.print_help()
        print("\nExamples:")
        print("  python download_price.py --year 2024")
        print("  python download_price.py --range 2020 2024")
        return

    years_to_download = []

    if args.year:
        years_to_download.append(args.year)

    if args.range:
        start_year, end_year = args.range
        if start_year > end_year:
            start_year, end_year = end_year, start_year
        years_to_download.extend(range(start_year, end_year + 1))

    # Remove duplicates and sort
    years_to_download = sorted(set(years_to_download))

    if years_to_download:
        print(f"Preparing to download years: {years_to_download}")
        download_years(years_to_download)


if __name__ == "__main__":
    main()
