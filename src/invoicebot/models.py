from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class InvoiceLineInput(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)


class InvoiceInput(BaseModel):
    invoice_type: str
    customer_name: str = Field(min_length=1, max_length=200)
    customer_address: str = Field(min_length=1, max_length=500)
    invoice_date: date
    due_date: date
    salesperson: str = Field(min_length=1, max_length=100)
    job: str = Field(min_length=1, max_length=200)
    payment_terms: str = Field(min_length=1, max_length=200)
    lines: list[InvoiceLineInput] = Field(min_length=1, max_length=15)
    purchase_reference: str = ""

    @field_validator("invoice_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        value = value.upper().strip()
        if value not in {"S", "U", "T", "P", "C"}:
            raise ValueError("invoice_type must be S, U, T, P, or C")
        return value

