import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the Excel file
df = pd.read_excel("data/company_reports_revenue.xlsx")

# Display basic info about the data
print("Initial data preview:")
print(df.head())
print("\nSummary statistics:")
print(df.describe())

# If fiscal_year is a datetime, extract the year as an integer.
if np.issubdtype(df["fiscal_year"].dtype, np.datetime64):
    df["year"] = df["fiscal_year"].dt.year
else:
    # Attempt to convert to datetime and then extract the year.
    df["fiscal_year"] = pd.to_datetime(df["fiscal_year"], errors="coerce")
    df["year"] = df["fiscal_year"].dt.year

# Sort data by company_name and the extracted year
df = df.sort_values(["company_name", "year"]).reset_index(drop=True)

# Create a column for the base-10 logarithm of revenue
df["log_rev"] = np.log10(df["revenue"])

def detect_and_adjust_shifts(group, threshold=2.5):
    """
    For a given company's data (group), this function:
    - Sorts by fiscal year.
    - Identifies contiguous blocks where the scale (order of magnitude) is consistent.
    - Computes a block median of the log10(revenue) values.
    - Uses the first block as a reference and computes an adjustment factor to align all values to that block.
    - Returns the group with additional columns: 'block', 'adjustment_factor', and 'adj_revenue'.
    """
    group = group.sort_values("year").reset_index(drop=True)
    
    # Detect blocks: start a new block when the change in log_rev is large.
    blocks = [0]  # first row starts block 0
    for i in range(1, len(group)):
        if abs(group.loc[i, "log_rev"] - group.loc[i-1, "log_rev"]) > threshold:
            blocks.append(blocks[-1] + 1)
        else:
            blocks.append(blocks[-1])
    group["block"] = blocks
    
    # Compute median log revenue for each block.
    block_medians = group.groupby("block")["log_rev"].median()
    
    # Use the first block (block 0) as the reference.
    ref_median = block_medians.loc[0]
    
    # Compute the adjustment factor per row: 
    # adjustment_factor = 10^(ref_median - block_median) for the row's block.
    group["adjustment_factor"] = group["block"].map(lambda b: 10**(ref_median - block_medians.loc[b]))
    
    # Compute the adjusted revenue.
    group["adj_revenue"] = group["revenue"] * group["adjustment_factor"]
    return group

# Apply the adjustment procedure for each company.
adjusted_df = df.groupby("company_name", group_keys=False).apply(detect_and_adjust_shifts)

# Let's inspect a few rows of the adjusted data
print("\nAdjusted Data Preview:")
print(adjusted_df.head(10))

# Sample a few companies for plotting - here, we'll pick the first 3 unique companies.
sample_companies = adjusted_df["company_name"].unique()[:3]

# For each company, plot raw and adjusted revenue over the years.
for company in sample_companies:
    comp_data = adjusted_df[adjusted_df["company_name"] == company]
    
    # Plot raw revenue
    plt.figure()
    plt.plot(comp_data["year"], comp_data["revenue"], marker='o', linestyle='-')
    plt.title(f"Raw Revenue for {company}")
    plt.xlabel("Fiscal Year")
    plt.ylabel("Revenue")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    
    # Plot adjusted revenue
    plt.figure()
    plt.plot(comp_data["year"], comp_data["adj_revenue"], marker='o', linestyle='-')
    plt.title(f"Adjusted Revenue for {company}")
    plt.xlabel("Fiscal Year")
    plt.ylabel("Adjusted Revenue")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
