import json
import pandas as pd

# Load the JSON file
with open('data/director_education_summaries_all/all_directors_education_summary.json') as f:
    data = json.load(f)

# Expand each director record into one row per active year
rows = []
for d in data:
    # Assume if an attribute is missing, then it is False.
    first = d['first_year']
    last = d['last_year']
    for year in range(first, last + 1):
        rows.append({
            'company': d['company'],
            'year': year,
            'has_technical_education': d.get('has_technical_education', False),
            'has_business_education': d.get('has_business_education', False),
            'has_other_higher_education': d.get('has_other_higher_education', False),
            'has_non_swedish_experience': d.get('has_non_swedish_experience', False),
            'has_usa_experience': d.get('has_usa_experience', False)
        })

# Create a DataFrame
df = pd.DataFrame(rows)

# Group by company and year, counting total board members and summing the flags
grouped = df.groupby(['company', 'year']).agg(
    total_members=('year', 'count'),
    count_technical=('has_technical_education', 'sum'),
    count_business=('has_business_education', 'sum'),
    count_other=('has_other_higher_education', 'sum'),
    count_non_swedish=('has_non_swedish_experience', 'sum'),
    count_usa=('has_usa_experience', 'sum')
).reset_index()

# Calculate the share (proportion) for each category
grouped['share_technical'] = grouped['count_technical'] / grouped['total_members']
grouped['share_business'] = grouped['count_business'] / grouped['total_members']
grouped['share_other'] = grouped['count_other'] / grouped['total_members']
grouped['share_non_swedish'] = grouped['count_non_swedish'] / grouped['total_members']w
grouped['share_usa'] = grouped['count_usa'] / grouped['total_members']

# Optional: sort the results for easier viewing
grouped.sort_values(['company', 'year'], inplace=True)
print(grouped)

# Save the results to a excel file
grouped.to_excel('data/director_education_summaries_all/all_education_shares.xlsx', index=False)