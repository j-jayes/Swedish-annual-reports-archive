import pandas as pd
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess
from sklearn.cluster import KMeans

# Load the data (assumes your main dataset is in Parquet format)
df = pd.read_parquet('data/company_reports_smoothed.parquet')

# Convert fiscal_year to datetime (assuming January 1st of the fiscal year)
df['fiscal_year'] = pd.to_datetime(df['fiscal_year'].astype(str), format='%Y')

# Identify numeric columns (excluding company_name and fiscal_year)
exclude_cols = ['company_name', 'fiscal_year']
num_cols = [col for col in df.columns if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])]

# Create a copy for processing
df_smoothed = df.copy()

def adjust_scale(series):
    """
    Adjusts a numeric series for potential scale shifts.
    Uses a 2-cluster KMeans on the log10 of positive values and, if clusters differ substantially,
    scales the cluster with lower values up.
    """
    series_adjusted = series.copy()
    valid = series[series > 0].dropna()
    if valid.shape[0] < 10:
        return series_adjusted
    # Log-transform positive values
    log_vals = np.log10(valid.values).reshape(-1, 1)
    
    # Run KMeans with 2 clusters
    kmeans = KMeans(n_clusters=2, random_state=0).fit(log_vals)
    labels = kmeans.labels_
    centers = kmeans.cluster_centers_.flatten()
    
    # Check if clusters are sufficiently separated (e.g., threshold of 2.5 in log10 space)
    if np.abs(centers[0] - centers[1]) < 2.5:
        return series_adjusted
    
    # Identify the lower cluster and compute the multiplicative factor
    lower_cluster = np.argmin(centers)
    # The factor is 10 raised to the difference in centers (ensuring positive factor)
    factor = 10 ** (np.abs(centers.max() - centers.min()))
    
    # Adjust the lower cluster values
    lower_indices = valid.index[labels == lower_cluster]
    series_adjusted.loc[lower_indices] = series_adjusted.loc[lower_indices] * factor
    return series_adjusted

def winsorize(series, threshold=3.0):
    """
    Winsorizes the series by capping extreme values based on the median and median absolute deviation (MAD).
    """
    med = series.median()
    mad = np.median(np.abs(series - med))
    if mad == 0:
        mad = series.std()  # Fallback if MAD is zero
    lower_bound = med - threshold * mad
    upper_bound = med + threshold * mad
    return series.clip(lower=lower_bound, upper=upper_bound)

def smooth_series(dates, values, frac=0.3):
    """
    Smooths the data using LOWESS.
    :param dates: numeric x-values (e.g. fiscal_year converted to ordinal)
    :param values: the numeric series values
    :param frac: fraction of data used when estimating each y-value.
    """
    if len(values) < 5:
        return values
    smoothed = lowess(values, dates, frac=frac, return_sorted=False)
    return smoothed

# Process each company separately
result_frames = []
for company, group in df_smoothed.groupby('company_name'):
    group = group.sort_values('fiscal_year')
    # Convert fiscal_year to a numeric format for smoothing (ordinal)
    dates_ordinal = group['fiscal_year'].map(pd.Timestamp.toordinal)
    for col in num_cols:
        # Adjust for scale shifts
        adjusted = adjust_scale(group[col])
        # Remove or limit outliers using winsorization
        cleaned = winsorize(adjusted)
        # Smooth the series using LOWESS
        smoothed = smooth_series(dates_ordinal, cleaned)
        # Save the smoothed data in a new column, e.g., revenue_smoothed
        group[col + '_smoothed'] = smoothed
    result_frames.append(group)

df_final = pd.concat(result_frames)

# Save the final result to a Parquet file
output_file = 'data/company_reports_smoothed_output.parquet'
df_final.to_parquet(output_file)

# Optionally, display a sample of the output to verify the changes
print(df_final.head())