"""State management for the LangGraph Code Generator workflow."""

from typing import Dict, List, Any, TypedDict, Optional
from pydantic import BaseModel


class CodeGenerationState(TypedDict):
    """State for the code generation workflow."""
    user_prompt: str
    generated_code: str
    syntax_errors: List[str]
    execution_results: Dict[str, Any]
    current_node: str
    retry_count: int
    # New fields for code rectification
    execution_errors: List[str]
    rectified_code: str
    rectification_attempts: int
    error_analysis: Dict[str, Any]


class CodeExecutionRequest(BaseModel):
    """Request model for code execution."""
    code: str
    timeout: int = 30


class CodeExecutionResponse(BaseModel):
    """Response model for code execution."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float


class CodeRectificationRequest(BaseModel):
    """Request model for code rectification."""
    original_code: str
    error_message: str
    error_type: str
    execution_context: Dict[str, Any]


class CodeRectificationResponse(BaseModel):
    """Response model for code rectification."""
    success: bool
    rectified_code: Optional[str] = None
    changes_made: List[str] = []
    error_analysis: Dict[str, Any] = {}
    confidence_score: float = 0.0