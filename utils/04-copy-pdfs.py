import os
import shutil
import pandas as pd

# Define paths
excel_path = "/Users/jonathanjayes/Documents/PhD/Swedish-annual-reports-archive/data/temp/raw_pdf_filenames_edit_with_years_edit.xlsx"
raw_folder = "/Users/jonathanjayes/Documents/PhD/Swedish-annual-reports-archive/data/raw"
processed_folder = "/Volumes/Lenovo PS8/company-reports/processed"

# Load the Excel file
df = pd.read_excel(excel_path)

# Function to safely generate new filenames
def generate_new_filename(company_name, year, original_filename):
    if pd.isna(company_name) or pd.isna(year):
        return None  # Skip files with missing data
    
    sanitized_company = "".join(c if c.isalnum() or c in " -_" else "" for c in str(company_name))
    new_filename = f"{sanitized_company.strip()}-{int(year)}.pdf"
    return new_filename

# Ensure the processed folder exists
os.makedirs(processed_folder, exist_ok=True)

# Process files
for _, row in df.iterrows():
    original_filename = row['filename']
    company_name = row['company_name']
    extracted_year = row['extracted_year']
    
    new_filename = generate_new_filename(company_name, extracted_year, original_filename)
    
    if new_filename:
        src_path = os.path.join(raw_folder, str(original_filename))
        dest_path = os.path.join(processed_folder, new_filename)
        
        if os.path.exists(src_path):
            shutil.copy2(src_path, dest_path)
            print(f"Copied: {original_filename} -> {new_filename}")
        else:
            print(f"File not found: {src_path}")
    else:
        print(f"Skipping: {original_filename} (Missing company or year)")

print("File processing complete!")
