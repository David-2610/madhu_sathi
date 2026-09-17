"""
Common schemas and standard error envelopes for Honey Chain API.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ValidationErrorDetail(BaseModel):
    """Field-level schema validation error detail."""

    loc: List[Union[str, int]] = Field(..., description="Location of the validation error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type identifier")


class ErrorResponse(BaseModel):
    """Standardized error envelope returned by the API."""

    detail: Union[str, List[ValidationErrorDetail]] = Field(
        ...,
        description="Error description string or array of field validation errors",
        examples=["Resource not found.", "Invalid state transition."],
    )


class MessageResponse(BaseModel):
    """Standard generic success response envelope."""

    message: str = Field(..., description="Success message", examples=["Operation completed successfully."])
