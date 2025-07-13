# Check which directory is allowed for import/export operations in MySQL
SHOW VARIABLES LIKE 'secure_file_priv';

# Create a table named '2023part1' to store property transaction data
CREATE TABLE 2023part1 (
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
  `District` VARCHAR(255),
  `County` VARCHAR(255),
  `PPD Category Type` VARCHAR(50),
  `Record Status` VARCHAR(10)
);
# Load data from a CSV file into the '2023part1' table
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/2023part1.csv'
INTO TABLE `2023part1`
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"' 
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
# Remove unnecessary columns from the '2023part1' table
ALTER TABLE `2023part1` DROP COLUMN PAON;
ALTER TABLE `2023part1` DROP COLUMN SAON;
ALTER TABLE `2023part1` DROP COLUMN Street;
ALTER TABLE `2023part1` DROP COLUMN Locality;
ALTER TABLE `2023part1` DROP COLUMN `PPD Category Type`;
ALTER TABLE `2023part1` DROP COLUMN `Record Status`;
# Clean up text fields by trimming spaces and converting to lowercase
UPDATE `2023part1`
SET County = lower(trim(County)), District = lower(trim(District)), `Town/City` = lower(trim(`Town/City`));

# Create a table named '2023part2' to store property transaction data
CREATE TABLE 2023part2 (
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
  `District` VARCHAR(255),
  `County` VARCHAR(255),
  `PPD Category Type` VARCHAR(50),
  `Record Status` VARCHAR(10)
);
# Load data from a CSV file into the '2023part2' table
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/2023part2.csv'
INTO TABLE `2023part2`
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"' 
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
# Remove unnecessary columns from the '2023part2' table
ALTER TABLE `2023part2` DROP COLUMN PAON;
ALTER TABLE `2023part2` DROP COLUMN SAON;
ALTER TABLE `2023part2` DROP COLUMN Street;
ALTER TABLE `2023part2` DROP COLUMN Locality;
ALTER TABLE `2023part2` DROP COLUMN `PPD Category Type`;
ALTER TABLE `2023part2` DROP COLUMN `Record Status`;
# Clean up text fields by trimming spaces and converting to lowercase
UPDATE `2023part2`
SET County = lower(trim(County)), District = lower(trim(District)), `Town/City` = lower(trim(`Town/City`));