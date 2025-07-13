# Merge
# Vertically merge tables into 2023_london
CREATE TABLE `2023_london` AS
SELECT *
FROM `2023part1`
UNION
SELECT *
FROM `2023part2`;

# Check for duplicate data (Using UNION ALL in 2021 may cause duplicates)
SELECT `Transaction unique identifier`, COUNT(`Transaction unique identifier`) AS Amount
FROM `2023_london`
GROUP BY `Transaction unique identifier`
HAVING Amount > 1;

# Rename Westminster
UPDATE `2023_london`
SET District = 'westminster'
WHERE District = 'city of westminster';

# Check if Westminster was successfully renamed
SELECT *
FROM `2023_london`
WHERE District = 'westminster';

# Create 'outward code' column
ALTER TABLE `2023_london` ADD COLUMN `Outward Code` varchar(5);
# Check the relationship between postcode and borough
SELECT DISTINCT District, SUBSTRING(Postcode,1, INSTR(Postcode,' ')-1) AS Postcode
FROM `2023_london`
ORDER BY District, Postcode ASC;

# Assign values to the 'outward code'
UPDATE `2023_london`
SET `Outward Code` = SUBSTRING(Postcode, 1, INSTR(Postcode,' ')-1);

# Table check: Are there any districts that belong to the 33 London boroughs but have a county outside of London?
SELECT DISTINCT london.District, london.County
FROM `2023_london` AS london
INNER JOIN borough_mapping AS map
ON london.District = map.borough
WHERE County <> 'greater london';

# Does Greater London include any districts outside the 33 boroughs?  
SELECT DISTINCT london.District, london.County
FROM `2023_london` AS london
LEFT JOIN borough_mapping AS map
ON london.District = map.borough
WHERE County = 'greater london' AND map.borough IS NULL;

# Filter data based on Venn diagram logic
CREATE TABLE `2023_london_filtered`
SELECT 
    london.*, oc.state,
    (CASE
        WHEN (london.County = 'greater london') AND (bm.borough IS NOT NULL) AND (oc.outward_code IS NOT NULL) THEN 'cbp'
        WHEN (london.County = 'greater london') AND (bm.borough IS NOT NULL) THEN 'cb'
        WHEN (london.County = 'greater london') AND (oc.outward_code IS NOT NULL) THEN 'cp'
        WHEN (bm.borough IS NOT NULL) AND (oc.outward_code IS NOT NULL) THEN 'bp'
        WHEN (london.County = 'greater london') THEN 'c'
        WHEN (bm.borough IS NOT NULL) THEN 'b'
        WHEN (oc.outward_code IS NOT NULL) THEN 'p'
        ELSE 'null' END) AS source_flag
FROM `2023_london` AS london
LEFT JOIN `borough_mapping` AS bm
  ON london.District = bm.borough
LEFT JOIN `outward_code` AS oc
  ON london.`Outward Code` = oc.outward_code
WHERE
    london.County = 'greater london'
    OR bm.borough IS NOT NULL
    OR oc.outward_code IS NOT NULL;

# Check for duplicate data
SELECT `Transaction unique identifier`, COUNT(`Transaction unique identifier`) AS Amount
FROM `2023_london_filtered`
GROUP BY `Transaction unique identifier`
HAVING Amount >1;

# Verify each entry in source_flag
SELECT source_flag, COUNT(source_flag)
FROM `2023_london_filtered`
GROUP BY source_flag;

# Check if all 'cb' values are null (there are 3 records)
SELECT source_flag, `Outward Code`, COUNT(source_flag)
FROM `2023_london_filtered`
WHERE source_flag = 'cb'
GROUP BY source_flag, `Outward Code`;

# Delete records where 'Outward Code' has a value, excluding nulls
DELETE FROM `2023_london_filtered`
WHERE source_flag = 'cb' AND `Outward Code` <>'';

# Check if 'source_flag' contains any values other than 'p' when state = 'outer'
SELECT state, source_flag, COUNT(source_flag)
FROM  `2023_london_filtered`
WHERE state = 'outer'
GROUP BY state, source_flag;

# Delete records that are outside London and have state = 'outer'
DELETE FROM  `2023_london_filtered`
WHERE source_flag = 'p' AND state = 'outer';

# Create a date column
ALTER TABLE `2023_london_filtered`ADD COLUMN `Transfer Date` DATE;
# Check the extraction status of 'Date of Transform'
SELECT SUBSTRING(`Date of Transfer`,1,10) AS new_date
FROM `2023_london_filtered`;

# Assign values to 'Transfer Date'
UPDATE `2023_london_filtered`
SET `Transfer Date` = SUBSTRING(`Date of Transfer`,1,10);
UPDATE `2023_london_filtered`
SET `Transfer Date` = STR_TO_DATE(`Transfer Date`, '%Y-%m-%d');

# View the output table
SELECT *
FROM `2023_london_filtered`;
