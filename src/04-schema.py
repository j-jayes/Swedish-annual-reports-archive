from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class IncomeStatement(BaseModel):
    """
    Standard representation of an Income Statement. 
    Board members are often listed below this statement in older reports.
    """
    revenue: Optional[float] = Field(None, description="Total revenues or sales.")
    cost_of_goods_sold: Optional[float] = Field(None, description="Cost of goods sold.")
    operating_expenses: Optional[float] = Field(None, description="Total operating expenses.")
    wages_expense: Optional[float] = Field(None, description="Total wages and salaries expense.")
    net_income: Optional[float] = Field(None, description="Net income (profit or loss) for the period.")
    additional_details: Optional[Dict[str, float]] = Field(
        None, 
        description="Other income statement items or subcategories, e.g., interest or tax expenses."
    )

class BalanceSheet(BaseModel):
    """
    Standard representation of a Balance Sheet.
    """
    total_assets: Optional[float] = Field(None, description="Total assets at period end.")
    current_assets: Optional[float] = Field(None, description="Current assets.")
    fixed_assets: Optional[float] = Field(None, description="Long-term or fixed assets.")
    total_liabilities: Optional[float] = Field(None, description="Total liabilities.")
    current_liabilities: Optional[float] = Field(None, description="Current liabilities.")
    long_term_liabilities: Optional[float] = Field(None, description="Long-term liabilities.")
    shareholders_equity: Optional[float] = Field(None, description="Total shareholders' or owners' equity.")
    additional_details: Optional[Dict[str, float]] = Field(
        None, 
        description="Other balance sheet items, e.g., inventory, receivables, or other assets."
    )

class BoardMember(BaseModel):
    """
    Representation of a single board member.
    Typically listed after the Income Statement in older reports.
    """
    surname: str = Field(..., description="The surname of the board member.")
    first_name: Optional[str] = Field(None, description="The first name of the board member.")
    initials: Optional[str] = Field(None, description="Initials of the board member.")
    position: Optional[str] = Field(None, description="The board position held by the member.")

class Auditor(BaseModel):
    """
    Representation of a single auditor, typically listed after the board.
    """
    surname: str = Field(..., description="The surname of the auditor.")
    first_name: Optional[str] = Field(None, description="The first name of the auditor.")
    initials: Optional[str] = Field(None, description="Initials of the auditor.")
    auditing_firm: Optional[str] = Field(None, description="The auditing firm, if specified.")

class FinancialReport(BaseModel):
    """
    Comprehensive financial report model, including:
    - Income Statement
    - Balance Sheet
    - Optional: Number of employees
    - Board members (often listed under the P&L statement)
    - Auditors (often follow after the board list)
    """
    company_name: str = Field(..., description="The name of the company.")
    fiscal_year: int = Field(..., description="Fiscal year of the report.")
    income_statement: IncomeStatement = Field(..., description="Income statement details.")
    balance_sheet: BalanceSheet = Field(..., description="Balance sheet details.")
    number_of_employees: Optional[int] = Field(None, description="Total number of employees.")
    board: Optional[List[BoardMember]] = Field(None, description="List of board members with details.")
    auditors: Optional[List[Auditor]] = Field(None, description="List of auditors with details.")
    additional_notes: Optional[str] = Field(None, description="Any extra commentary or notes from the report.")
