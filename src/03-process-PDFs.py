import os
import pandas as pd
from bs4 import BeautifulSoup

def create_company_names():
    # Read the HTML file
    with open('data/temp/SHoFDB - Historical annual reports archive.html', 'r') as file:
        html = file.read()

    # Create a BeautifulSoup object and parse the HTML
    soup = BeautifulSoup(html, 'html.parser')

    # Find all of the text inside the h4 tag with class "panel-title"
    company_names = [name.get_text(strip=True) for name in soup.find_all('h4', class_='panel-title')]

    # Create a DataFrame from the list of company names
    company_names_df = pd.DataFrame(company_names, columns=['company_name'])

    # Save the DataFrame to an excel file
    company_names_df.to_excel('data/temp/company_names.xlsx', index=False)

def create_raw_pdf_filenames():
    # Get a list of all files in the directory with .pdf extension
    file_list = [filename for filename in os.listdir('data/raw') if filename.endswith('.pdf')]

    # Create a DataFrame from this list and sort it by filename
    df = pd.DataFrame(file_list, columns=['filename']).sort_values(by='filename').reset_index(drop=True)

    # create a new column called "pattern" with the file name, excluding the extension
    df['pattern'] = df['filename'].str.replace('.pdf', '')

    # drop any 4 digit number from the pattern, as well as any punctuation or alphabetic characters touching the digits
    df['pattern'] = df['pattern'].str.replace(r'\d{4}', '', regex=True)

    # remove "AB" from the pattern
    df['pattern'] = df['pattern'].str.replace('AB', '')

    # make the pattern lower case
    df['pattern'] = df['pattern'].str.lower()

    # trim the whitespace from the pattern
    df['pattern'] = df['pattern'].str.strip()

    # Save the DataFrame to an excel file
    df.to_excel('data/temp/raw_pdf_filenames.xlsx', index=False)


# run both functions
create_company_names()
create_raw_pdf_filenames()