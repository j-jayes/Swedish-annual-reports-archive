import os
import json
import logging
import asyncio
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Tuple

# Import Gemini API client
from google import genai

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

# Create a Gemini API client
client = genai.Client(api_key=api_key)

# Paths and model configuration
PROCESSED_PATH = "/Volumes/Lenovo PS8/company-reports/processed"
OUTPUT_PATH = "/Volumes/Lenovo PS8/company-reports/structured"
MODEL_ID = "gemini-2.0-flash"

# Make sure output path exists
os.makedirs(OUTPUT_PATH, exist_ok=True)

# ----------------- Pydantic Data Models -----------------

class IncomeStatement(BaseModel):
    revenue: Optional[float] = Field(None, description="Total revenues or sales. (Swedish: Intäkter)")
    cost_of_goods_sold: Optional[float] = Field(None, description="Cost of goods sold. (Swedish: Kostnad såld vara)")
    operating_expenses: Optional[float] = Field(None, description="Total operating expenses. (Swedish: Rörelsekostnader)")
    wages_expense: Optional[float] = Field(None, description="Total wages and salaries expense. (Swedish: Lönekostnader)")
    tax_expense: Optional[float] = Field(None, description="Tax expense. (Swedish: Skatt)")
    depreciation: Optional[float] = Field(None, description="Depreciation (Swedish: Avskrivningar)")
    net_income: Optional[float] = Field(None, description="Net income (profit or loss) for the period. (Swedish: Årets resultat)")

class BalanceSheet(BaseModel):
    total_assets: Optional[float] = Field(None, description="Total assets at period end. (Swedish: Tillgångar)")
    current_assets: Optional[float] = Field(None, description="Current assets. (Swedish: Omsättningstillgångar)")
    fixed_assets: Optional[float] = Field(None, description="Long-term or fixed assets. (Swedish: Anläggningstillgångar)")
    total_liabilities: Optional[float] = Field(None, description="Total liabilities. (Swedish: Skulder)")
    current_liabilities: Optional[float] = Field(None, description="Current liabilities. (Swedish: Kortfristiga skulder)")
    long_term_liabilities: Optional[float] = Field(None, description="Long-term liabilities. (Swedish: Långfristiga skulder)")
    shareholders_equity: Optional[float] = Field(None, description="Total shareholders' or owners' equity. (Swedish: Eget kapital)")

class BoardMember(BaseModel):
    surname: str = Field(..., description="The surname of the board member.")
    first_name: Optional[str] = Field(None, description="The first name of the board member.")
    initials: Optional[str] = Field(None, description="Initials of the board member.")
    position: Optional[str] = Field(None, description="The board position held by the member.")

class Auditor(BaseModel):
    surname: str = Field(..., description="The surname of the auditor.")
    first_name: Optional[str] = Field(None, description="The first name of the auditor.")
    initials: Optional[str] = Field(None, description="Initials of the auditor.")
    auditing_firm: Optional[str] = Field(None, description="The auditing firm, if specified.")

class Employees(BaseModel):
    n_employees: Optional[int] = Field(None, description="Total number of employees. (Swedish: Antal anställda)")
    n_blue_collar_workers: Optional[int] = Field(None, description="Total number of blue collar workers. (Swedish: Antal arbetare)")
    n_white_collar_workers: Optional[int] = Field(None, description="Total number of white collar workers. (Swedish: Antal tjänstemän)")

class FinancialReport(BaseModel):
    company_name: str = Field(..., description="The name of the company.")
    fiscal_year: int = Field(..., description="Fiscal year of the report.")
    income_statement: IncomeStatement = Field(..., description="Income statement details.")
    balance_sheet: BalanceSheet = Field(..., description="Balance sheet details.")
    employees: Optional[Employees] = Field(None, description="Employee details.")
    board: Optional[List[BoardMember]] = Field(None, description="List of board members with details.")
    auditors: Optional[List[Auditor]] = Field(None, description="List of auditors with details.")
    additional_notes: Optional[str] = Field(None, description="Any extra commentary or notes from the report.")

# ----------------- Helper Functions -----------------

def save_json(output_file_path: str, json_object: dict):
    """Blocking file I/O function to save JSON content."""
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(json_object, f, ensure_ascii=False, indent=2)

# ----------------- Asynchronous Extraction Functions -----------------

async def generate_response(file_path: str, uploaded_file, attempt: int, model: BaseModel) -> Tuple[int, Any]:
    """
    Asynchronously calls the Gemini API to generate a structured response.
    """
    prompt = (
        "You are an expert at extracting structured data from Swedish financial reports from the 20th century, world-class even, really excellent. \n\n"
        "Please extract the information from the provided PDF file according to the pydantic data model. \n\n"
        "When you are faced with high levels of detail, extract the primary number or value in each category, e.g. total revenue, total assets, etc."
    )
    # Wrap the blocking API call in a thread
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_ID,
        contents=[prompt, uploaded_file],
        config={
            'response_mime_type': 'application/json',
            'response_schema': model
        }
    )
    logger.info(f"Generated response {attempt} for file {os.path.basename(file_path)}.")
    return attempt, response.parsed

async def extract_structured_data(file_path: str, model: BaseModel, num_responses: int = 1) -> List[Any]:
    """
    Asynchronously uploads a PDF file, concurrently generates multiple structured responses,
    saves each response as soon as it is ready, and then deletes the uploaded file.
    """
    # Upload the file (blocking call wrapped in a thread)
    uploaded_file = await asyncio.to_thread(
        client.files.upload,
        file=file_path,
        config={'display_name': os.path.basename(file_path).replace('.pdf', '')}
    )

    # Launch concurrent tasks for each extraction attempt
    tasks = [
        asyncio.create_task(generate_response(file_path, uploaded_file, attempt, model))
        for attempt in range(1, num_responses + 1)
    ]

    # Process responses as they complete
    responses = {}
    for task in asyncio.as_completed(tasks):
        attempt, parsed_data = await task
        responses[attempt] = parsed_data

        # Save each response immediately
        json_object = parsed_data.model_dump()
        json_filename = os.path.basename(file_path).replace(".pdf", f"_{attempt}.json")
        output_file_path = os.path.join(OUTPUT_PATH, json_filename)
        await asyncio.to_thread(save_json, output_file_path, json_object)
        logger.info(f"Saved {json_filename}.")

    # Delete the uploaded file after processing all responses
    await asyncio.to_thread(client.files.delete, name=uploaded_file.name)
    logger.info(f"Deleted uploaded file {uploaded_file.name}.")

    # Return the responses in order (1, 2, ..., num_responses)
    return [responses[i] for i in range(1, num_responses + 1)]

# ----------------- Asynchronous Processing of PDFs -----------------

async def process_single_pdf(pdf_filename: str):
    """
    Asynchronously processes a single PDF file:
    - Checks if the first output JSON exists (to skip if already processed).
    - Calls extract_structured_data to generate and save responses concurrently.
    """
    pdf_path = os.path.join(PROCESSED_PATH, pdf_filename)
    output_file_path_first = os.path.join(OUTPUT_PATH, pdf_filename.replace(".pdf", "_1.json"))
    if os.path.exists(output_file_path_first):
        logger.info(f"Output for {pdf_filename} already exists. Skipping.")
        return

    logger.info(f"Processing {pdf_filename}...")
    try:
        await extract_structured_data(pdf_path, FinancialReport, num_responses=3)
    except Exception as e:
        logger.error(f"Failed to process {pdf_filename}: {e}")

async def process_financial_reports():
    """
    Asynchronously reads the Excel file with PDF filenames,
    then concurrently processes each PDF file.
    """
    excel_path = "data/temp/filenames_to_loop_through.xlsx"
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        logger.error(f"Failed to read Excel file {excel_path}: {e}")
        return

    tasks = []
    for _, row in df.iterrows():
        pdf_filename = row["filename"]
        tasks.append(asyncio.create_task(process_single_pdf(pdf_filename)))
    await asyncio.gather(*tasks)

# ----------------- Main Entry Point -----------------

if __name__ == "__main__":
    asyncio.run(process_financial_reports())
