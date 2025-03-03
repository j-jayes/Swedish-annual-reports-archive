import re
import pandas as pd
import os

# get the filenames from "/Volumes/Lenovo PS8/company-reports/processed" that end in ".pdf"
filenames = [f for f in os.listdir("/Volumes/Lenovo PS8/company-reports/processed") if f.endswith(".pdf")]

# sort the filenames
filenames.sort()

# create a DataFrame with the filenames
filenames = pd.DataFrame(filenames, columns=["filename"])

# write to excel file at data/temp/filenames_to_loop_through.xlsx
filenames.to_excel("data/temp/filenames_to_loop_through.xlsx", index=False)
