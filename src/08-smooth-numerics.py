import os
import json
import logging
import statistics
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def load_json(file_path):
    """Load a JSON file from the given path."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return None

def process_numeric_field(field_path, reports, company, year):
    """
    Given a list of reports (dictionaries) and a field path (list of keys),
    extract non-null numeric values, check the discrepancy, and return an average.
    If discrepancy >= 20%, attempt smoothing using adjacent years.
    """
    values = []
    for report in reports:
        try:
            val = report
            for key in field_path:
                if val is None:
                    break
                val = val.get(key)
            if val is not None:
                values.append(val)
        except Exception as e:
            logging.error(f"Error processing field {'.'.join(field_path)} in {company} {year}: {e}")
    if not values:
        return None

    avg_val = statistics.mean(values)
    min_val = min(values)
    max_val = max(values)
    # Avoid division by zero
    if avg_val == 0:
        discrepancy = 0
    else:
        discrepancy = (max_val - min_val) / abs(avg_val)

    if discrepancy < 0.2:
        return avg_val
    else:
        logging.info(f"Discrepancy for field {'.'.join(field_path)} in {company} {year} is high ({discrepancy:.2f}); performing smoothing.")
        smoothed = smooth_numeric_field(field_path, company, year, current_values=values)
        if smoothed is not None:
            return smoothed
        else:
            logging.warning(f"Could not smooth field {'.'.join(field_path)} for {company} {year}; falling back to current average.")
            return avg_val

def smooth_numeric_field(field_path, company, year, current_values):
    """
    Attempt to smooth the numeric field by comparing current values to the average
    of the adjacent years’ values. It loads reports for adjacent years.
    If one side is missing (e.g. first or last year), it attempts to load two years from the available side.
    Returns the average of current values that fall within 20% of the adjacent average.
    """
    adjacent_values = []

    def load_year_reports(target_year):
        reports_year = []
        for i in [1, 2, 3]:
            filename = f"{company}-{target_year}_{i}.json"
            if os.path.exists(filename):
                rep = load_json(filename)
                if rep:
                    reports_year.append(rep)
            else:
                logging.debug(f"File {filename} not found.")
        return reports_year

    # Load adjacent reports from previous and next year
    prev_reports = load_year_reports(year - 1)
    next_reports = load_year_reports(year + 1)

    # If one side is missing, try two years from the available side
    if not prev_reports and next_reports:
        logging.info(f"No previous year reports for {company} {year}; trying next two years.")
        next_reports = load_year_reports(year + 1) + load_year_reports(year + 2)
        prev_reports = []  # explicitly empty
    elif not next_reports and prev_reports:
        logging.info(f"No next year reports for {company} {year}; trying previous two years.")
        prev_reports = load_year_reports(year - 1) + load_year_reports(year - 2)
        next_reports = []  # explicitly empty

    adjacent_reports = prev_reports + next_reports

    for rep in adjacent_reports:
        try:
            val = rep
            for key in field_path:
                if val is None:
                    break
                val = val.get(key)
            if val is not None:
                adjacent_values.append(val)
        except Exception as e:
            logging.error(f"Error processing adjacent field {'.'.join(field_path)} for {company} {year}: {e}")

    if not adjacent_values:
        logging.warning(f"No adjacent values found for {company} {year} field {'.'.join(field_path)}")
        return None

    adjacent_avg = statistics.mean(adjacent_values)
    # Choose current values within 20% of adjacent_avg
    valid_current = [v for v in current_values if abs(v - adjacent_avg) / abs(adjacent_avg) < 0.2]
    if valid_current:
        return statistics.mean(valid_current)
    else:
        logging.warning(f"No current values within 20%% of adjacent average for {company} {year} field {'.'.join(field_path)}")
        return None

def process_year_reports(company, year, base_dir, output_dir):
    """
    Process the three JSON reports for a given company and year.
    For numeric fields, apply discrepancy checking and smoothing if needed.
    For non-numeric fields (board, auditors), take the values from the _1.json file.
    Save the final summary to the specified output directory.
    """
    reports = []
    for i in [1, 2, 3]:
        filename = os.path.join(base_dir, f"{company}-{year}_{i}.json")
        if os.path.exists(filename):
            rep = load_json(filename)
            if rep:
                reports.append(rep)
            else:
                logging.warning(f"File {filename} could not be loaded.")
        else:
            logging.warning(f"File {filename} not found.")

    if not reports:
        logging.error(f"No reports found for {company} in year {year}. Skipping.")
        return

    # Use the _1.json file as the source for non-numeric fields.
    # If it is None, fall back to the first available non-None report.
    primary_report = reports[0] if reports[0] is not None else next((r for r in reports if r is not None), None)
    if primary_report is None:
        logging.error(f"No valid primary report found for {company} {year}. Skipping.")
        return

    summary = {
        "company_name": primary_report.get("company_name"),
        "fiscal_year": primary_report.get("fiscal_year"),
        "additional_notes": primary_report.get("additional_notes")
    }

    # Process numeric fields from income_statement, balance_sheet, and employees safely.
    income_data = primary_report.get("income_statement") or {}
    summary["income_statement"] = {}
    for key in income_data:
        summary["income_statement"][key] = process_numeric_field(["income_statement", key], reports, company, year)

    balance_data = primary_report.get("balance_sheet") or {}
    summary["balance_sheet"] = {}
    for key in balance_data:
        summary["balance_sheet"][key] = process_numeric_field(["balance_sheet", key], reports, company, year)

    employees_data = primary_report.get("employees") or {}
    summary["employees"] = {}
    for key in employees_data:
        summary["employees"][key] = process_numeric_field(["employees", key], reports, company, year)

    # For non-numeric fields, use the values from the _1.json report.
    summary["board"] = primary_report.get("board", [])
    summary["auditors"] = primary_report.get("auditors", [])

    output_file = os.path.join(output_dir, f"{company}-{year}_summary.json")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logging.info(f"Saved summary for {company} {year} to {output_file}")
    except Exception as e:
        logging.error(f"Error saving summary file {output_file}: {e}")

def main():
    base_dir = "/Volumes/Lenovo PS8/company-reports/structured"  # Directory where the JSON files are located.
    output_dir = "/Volumes/Lenovo PS8/company-reports/smoothed"
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")
        except Exception as e:
            logging.error(f"Failed to create output directory {output_dir}: {e}")
            return

    # Identify available JSON files based on the naming convention:
    # {company}-{year}_{i}.json, where i is in [1,2,3].
    files = os.listdir(base_dir)
    pattern = re.compile(r"([A-Za-z0-9]+)-(\d{4})_[123]\.json")
    company_years = {}
    for filename in files:
        match = pattern.match(filename)
        if match:
            company, year_str = match.groups()
            year = int(year_str)
            company_years.setdefault(company, set()).add(year)

    if not company_years:
        logging.error("No JSON files matching the expected naming pattern were found.")
        return

    # Loop through each company and year found
    for company, years in company_years.items():
        for year in sorted(years):
            logging.info(f"Processing {company} for year {year}")
            process_year_reports(company, year, base_dir, output_dir)

if __name__ == "__main__":
    main()
