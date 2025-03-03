import os
import re
import json
import pandas as pd

# Define the path where the files are located.
PATH = "/Volumes/Lenovo PS8/company-reports/smoothed"

# Read the Excel file containing the list of filenames.
filenames_df = pd.read_excel('data/temp/filenames_to_loop_through.xlsx')
# If the column is not named "filename", assume the first column contains the filenames.
if 'filename' not in filenames_df.columns:
    filenames_df.columns = ['filename']

# Add file_path column by joining the PATH and filename, and replace ".pdf" with "_summary.json"
filenames_df['file_path'] = filenames_df['filename'].apply(lambda x: os.path.join(PATH, x))
filenames_df['file_path'] = filenames_df['file_path'].apply(lambda x: x.replace(".pdf", "_summary.json"))

# Define a regex pattern to extract the company name and fiscal year from the filename.
# The expected format is something like "ASEA-1954_summary.json"
pattern = r"([^-\_]+)-(\d+)_summary\.json"

# List to collect records for each JSON file.
data_list = []

for index, row in filenames_df.iterrows():
    file_path = row['file_path']
    # Extract the filename from the path
    base_filename = os.path.basename(file_path)
    # Use regex to extract company and year from the filename.
    match = re.match(pattern, base_filename)
    if match:
        company_from_filename = match.group(1)
        fiscal_year_from_filename = int(match.group(2))
    else:
        print(f"Filename '{base_filename}' does not match the expected format.")
        continue

    # Check if the file exists.
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create a record dictionary and override company name and fiscal year with standardized values.
        record = {
            'company_name': company_from_filename,
            'fiscal_year': fiscal_year_from_filename
        }
        
        # Extract income statement values.
        income = data.get('income_statement', {})
        record['revenue'] = income.get('revenue')
        record['cost_of_goods_sold'] = income.get('cost_of_goods_sold')
        record['operating_expenses'] = income.get('operating_expenses')
        record['wages_expense'] = income.get('wages_expense')
        record['tax_expense'] = income.get('tax_expense')
        record['depreciation'] = income.get('depreciation')
        record['net_income'] = income.get('net_income')
        
        # Extract balance sheet values.
        balance = data.get('balance_sheet', {})
        record['total_assets'] = balance.get('total_assets')
        record['current_assets'] = balance.get('current_assets')
        record['fixed_assets'] = balance.get('fixed_assets')
        record['total_liabilities'] = balance.get('total_liabilities')
        record['current_liabilities'] = balance.get('current_liabilities')
        record['long_term_liabilities'] = balance.get('long_term_liabilities')
        record['shareholders_equity'] = balance.get('shareholders_equity')
        
        # Extract employee numbers.
        employees = data.get('employees', {})
        record['n_employees'] = employees.get('n_employees')
        record['n_blue_collar_workers'] = employees.get('n_blue_collar_workers')
        record['n_white_collar_workers'] = employees.get('n_white_collar_workers')
        
        data_list.append(record)
    else:
        print(f"File '{file_path}' not found.")

# Create a DataFrame from the collected records.
df = pd.DataFrame(data_list)

# Sort the DataFrame by company name and fiscal year.
df = df.sort_values(['company_name', 'fiscal_year'])


# Display the final DataFrame.
print(df)

# write to parquet
df.to_parquet('data/company_reports_smoothed.parquet', index=False)