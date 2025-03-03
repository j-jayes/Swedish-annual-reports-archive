import re
import pandas as pd

df = pd.read_excel("data/temp/raw_pdf_filenames_edit.xlsx")

# Define a function to extract the year from the filename
def extract_year(filename):
    match = re.search(r'(?<!\d)(18[7-9]\d|19\d{2}|20[01]\d|2020)(?!\d)', str(filename))
    return int(match.group()) if match else None

# Apply the function to create a new column for the year
df['extracted_year'] = df['filename'].apply(extract_year)

# Save the result to a new Excel file
df.to_excel("data/temp/raw_pdf_filenames_edit_with_years.xlsx", index=False)