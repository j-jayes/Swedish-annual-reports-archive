"""
This script concurrently extracts structured financial data from Swedish PDF financial reports using the Gemini API.

Overview:
    - Loads environment variables and initializes a Gemini API client with the provided API key.
    - Defines Pydantic data models to represent structured financial report data, including sections for:
        • Income Statement
        • Balance Sheet
        • Employees
        • Board Members
        • Auditors
    - Reads an Excel file (data/temp/filenames_to_loop_through.xlsx) containing a list of PDF filenames to process.
    - For each PDF file:
        • Checks if the first JSON output (with a '_1.json' suffix) already exists in the designated output directory.
        • If not, uploads the PDF file once and then performs three extraction attempts using the Gemini API.
        • Saves each extraction response as a JSON file with suffixes _1, _2, and _3 in the OUTPUT_PATH directory.
    - Utilizes asynchronous processing (with asyncio and to_thread) to concurrently handle multiple PDF files and reduce overall processing time.
    - Logs detailed information about the process and any errors encountered for easy debugging and monitoring.

Usage:
    Ensure that the OUTPUT_PATH directory exists and that you have the correct permissions.
    Execute the script directly; it will process all PDF files listed in the Excel file and output the corresponding JSON files.
"""


from google import genai
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Union, Tuple
import json
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


load_dotenv()

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

# Create a client
client = genai.Client(api_key=api_key)

PROCESSED_PATH = "/Volumes/Lenovo PS8/company-reports/processed"

OUTPUT_PATH = "/Volumes/Lenovo PS8/company-reports/structured"

MODEL_ID =  "gemini-2.0-flash" 

# make sure output path exists
os.makedirs(OUTPUT_PATH, exist_ok=True)


from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class IncomeStatement(BaseModel):
    """
    Standard representation of an Income Statement.
    Note: In many older reports, board member names are listed below this statement.
    """
    revenue: Optional[float] = Field(
        None, 
        description="Total revenues or sales. (Swedish: Intäkter)"
    )
    cost_of_goods_sold: Optional[float] = Field(
        None, 
        description="Cost of goods sold. (Swedish: Kostnad såld vara)"
    )
    operating_expenses: Optional[float] = Field(
        None, 
        description="Total operating expenses. (Swedish: Rörelsekostnader)"
    )
    wages_expense: Optional[float] = Field(
        None, 
        description="Total wages and salaries expense. (Swedish: Lönekostnader)"
    )
    tax_expense: Optional[float] = Field(None, description="Tax expense. (Swedish: Skatt)")
    depreciation: Optional[float] = Field(None, description="Depreciation (Swedish: Avskrivningar)")
    net_income: Optional[float] = Field(
        None, 
        description="Net income (profit or loss) for the period. (Swedish: Årets resultat)"
    )
    # additional_details: Optional[Dict[str, Union[float, Dict[str, Any]]]] = Field(
    #     None, 
    #     description="Other income statement items or subcategories, e.g., interest or tax expenses."
    # )

class BalanceSheet(BaseModel):
    """
    Standard representation of a Balance Sheet.
    """
    total_assets: Optional[float] = Field(
        None, 
        description="Total assets at period end. (Swedish: Tillgångar)"
    )
    current_assets: Optional[float] = Field(
        None, 
        description="Current assets. (Swedish: Omsättningstillgångar)"
    )
    fixed_assets: Optional[float] = Field(
        None, 
        description="Long-term or fixed assets. (Swedish: Anläggningstillgångar)"
    )
    total_liabilities: Optional[float] = Field(
        None, 
        description="Total liabilities. (Swedish: Skulder)"
    )
    current_liabilities: Optional[float] = Field(
        None, 
        description="Current liabilities. (Swedish: Kortfristiga skulder)"
    )
    long_term_liabilities: Optional[float] = Field(
        None, 
        description="Long-term liabilities. (Swedish: Långfristiga skulder)"
    )
    shareholders_equity: Optional[float] = Field(
        None, 
        description="Total shareholders' or owners' equity. (Swedish: Eget kapital)"
    )
    # additional_details: Optional[Dict[str, Union[float, Dict[str, Any]]]] = Field(
    #     None, 
    #     description="Other balance sheet items, e.g., inventory, receivables, or other assets. (Swedish: Övriga poster)"
    # )

class BoardMember(BaseModel):
    """
    Representation of a single board member.
    Typically listed below the Income Statement in older reports.
    """
    surname: str = Field(..., description="The surname of the board member.")
    first_name: Optional[str] = Field(None, description="The first name of the board member.")
    initials: Optional[str] = Field(None, description="Initials of the board member.")
    position: Optional[str] = Field(None, description="The board position held by the member.")

class Auditor(BaseModel):
    """
    Representation of a single auditor.
    Typically listed after the board members.
    """
    surname: str = Field(..., description="The surname of the auditor.")
    first_name: Optional[str] = Field(None, description="The first name of the auditor.")
    initials: Optional[str] = Field(None, description="Initials of the auditor.")
    auditing_firm: Optional[str] = Field(None, description="The auditing firm, if specified.")

class Employees(BaseModel):
    """
    Representation of the number of employees in a company.
    """
    n_employees: Optional[int] = Field(None, description="Total number of employees. (Swedish: Antal anställda)")
    n_blue_collar_workers: Optional[int] = Field(None, description="Total number of blue collar workers. (Swedish: Antal arbetare)")
    n_white_collar_workers: Optional[int] = Field(None, description="Total number of white collar workers. (Swedish: Antal tjänstemän)")

class FinancialReport(BaseModel):
    """
    Comprehensive financial report model, including:
    - Income Statement (with Swedish term references)
    - Balance Sheet (with Swedish term references)
    - Employees (with Swedish term references)
    - Board members (often listed under the P&L statement)
    - Auditors (often follow after the board list)
    """
    company_name: str = Field(..., description="The name of the company.")
    fiscal_year: int = Field(..., description="Fiscal year of the report.")
    income_statement: IncomeStatement = Field(..., description="Income statement details.")
    balance_sheet: BalanceSheet = Field(..., description="Balance sheet details.")
    employees: Optional[Employees] = Field(None, description="Employee details.")
    board: Optional[List[BoardMember]] = Field(None, description="List of board members with details.")
    auditors: Optional[List[Auditor]] = Field(None, description="List of auditors with details.")
    additional_notes: Optional[str] = Field(None, description="Any extra commentary or notes from the report.")

# --- Core functions ---
def extract_structured_data(file_path: str, model: BaseModel, num_responses: int = 1):
    """
    Uploads the PDF file once, then generates `num_responses` structured responses
    using the Gemini API. Returns a list of parsed Pydantic models.
    """
    # Upload the file with a display name derived from the filename (without extension)
    uploaded_file = client.files.upload(
        file=file_path,
        config={'display_name': os.path.basename(file_path).replace('.pdf', '')}
    )
    
    prompt = """
    You are an expert at extracting structured data from Swedish financial reports from the 20th century, world-class even, really excellent. 
    
    Please extract the information from the provided PDF file according to the pydantic data model. 
    
    When you are faced with high levels of detail, extract the primary number or value in each category, e.g. total revenue, total assets, etc.
    """
    
    responses = []
    for i in range(num_responses):
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt, uploaded_file],
            config={
                'response_mime_type': 'application/json',
                'response_schema': model
            }
        )
        responses.append(response.parsed)
        logger.info(f"Generated response {i+1} for file {os.path.basename(file_path)}.")
    
    # Delete the uploaded file from the client storage after processing all responses
    client.files.delete(name=uploaded_file.name)
    logger.info(f"Deleted uploaded file {uploaded_file.name}.")
    
    return responses

def process_financial_reports():
    """
    Reads the Excel file containing PDF filenames, processes each PDF to extract structured data three times,
    and saves each JSON output to the OUTPUT_PATH with filenames suffixed _1, _2, and _3.
    If the first JSON output for a PDF already exists, the file is skipped.
    """
    excel_path = "data/temp/filenames_to_loop_through.xlsx"
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        logger.error(f"Failed to read Excel file {excel_path}: {e}")
        return

    for index, row in df.iterrows():
        pdf_filename = row["filename"]
        pdf_path = os.path.join(PROCESSED_PATH, pdf_filename)
        # Check if the output JSON for the first response already exists
        output_file_path_first = os.path.join(OUTPUT_PATH, pdf_filename.replace(".pdf", "_1.json"))
        if os.path.exists(output_file_path_first):
            logger.info(f"Output for {pdf_filename} already exists. Skipping.")
            continue

        logger.info(f"Processing {pdf_filename}...")
        try:
            # Extract three structured responses from the PDF
            responses = extract_structured_data(pdf_path, FinancialReport, num_responses=3)
            
            # Save each response to its own JSON file
            for i, parsed_data in enumerate(responses, start=1):
                json_object = parsed_data.model_dump()
                json_filename = pdf_filename.replace(".pdf", f"_{i}.json")
                output_file_path = os.path.join(OUTPUT_PATH, json_filename)
                with open(output_file_path, "w", encoding="utf-8") as f:
                    json.dump(json_object, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved {json_filename}.")
        except Exception as e:
            logger.error(f"Failed to process {pdf_filename}: {e}")

if __name__ == "__main__":
    process_financial_reports()