"""
FastAPI Executor for LangGraph Code Generator
Provides a safe code execution endpoint and local execution function for workflow integration.
"""

from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Any, Dict
import traceback
import sys
import io

app = FastAPI()


class CodeRequest(BaseModel):
    code: str


class CodeExecutionResult(BaseModel):
    success: bool
    output: str
    error: str = ""


def execute_code(code: str) -> Dict[str, Any]:
    """
    Execute Python code safely and return result dict.
    Used by workflow for local (non-API) execution.
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    result = {"success": False, "output": "", "error": ""}
    try:
        exec(code, {})
        result["success"] = True
        result["output"] = sys.stdout.getvalue()
    except Exception as e:
        result["error"] = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return result


@app.post("/execute", response_model=CodeExecutionResult)
async def execute_code_api(request: CodeRequest):
    """
    FastAPI endpoint to execute code and return result.
    """
    result = execute_code(request.code)
    return CodeExecutionResult(**result)
