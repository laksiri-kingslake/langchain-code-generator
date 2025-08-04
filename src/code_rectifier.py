"""
Code Rectifier for fixing common execution errors.
Analyzes execution errors and provides automatic fixes.
"""

import re
import ast
import traceback
from typing import Dict, List, Any, Optional, Tuple
from src.config import Config
from src.state import CodeRectificationRequest, CodeRectificationResponse


class CodeRectifier:
    """Intelligent code rectifier that can analyze and fix common execution errors."""
    
    def __init__(self):
        self.config = Config()
        self.model = self.config.get_groq_model()
        
        # Common error patterns and their fixes
        self.error_patterns = {
            "from __future__ imports must occur at the beginning": self._fix_future_imports,
            "SyntaxError": self._analyze_syntax_error,
            "NameError": self._fix_name_error, 
            "ImportError": self._fix_import_error,
            "ModuleNotFoundError": self._fix_module_not_found,
            "IndentationError": self._fix_indentation_error,
            "AttributeError": self._fix_attribute_error,
            "TypeError": self._fix_type_error,
            "ValueError": self._fix_value_error,
            "KeyError": self._fix_key_error,
            "IndexError": self._fix_index_error,
        }
    
    def rectify_code(self, original_code: str, error_message: str, execution_context: Dict[str, Any] = None) -> CodeRectificationResponse:
        """
        Main method to rectify code based on execution errors.
        
        Args:
            original_code: The original code that failed
            error_message: The error message from execution
            execution_context: Additional context about the execution environment
            
        Returns:
            CodeRectificationResponse with rectified code and analysis
        """
        if execution_context is None:
            execution_context = {}
            
        # Analyze the error
        error_analysis = self._analyze_error(error_message, original_code)
        error_type = error_analysis.get("error_type", "Unknown")
        
        # Try pattern-based fixes first
        rectified_code, changes_made, confidence = self._apply_pattern_fixes(
            original_code, error_message, error_type
        )
        
        # If pattern fixes didn't work or confidence is low, use AI rectification
        if confidence < 0.7 or not rectified_code:
            ai_result = self._ai_rectify_code(original_code, error_message, error_analysis)
            if ai_result and ai_result.get("success", False):
                rectified_code = ai_result.get("code", rectified_code)
                changes_made.extend(ai_result.get("changes", []))
                confidence = max(confidence, ai_result.get("confidence", 0.5))
        
        return CodeRectificationResponse(
            success=bool(rectified_code and rectified_code != original_code),
            rectified_code=rectified_code,
            changes_made=changes_made,
            error_analysis=error_analysis,
            confidence_score=confidence
        )
    
    def _analyze_error(self, error_message: str, code: str) -> Dict[str, Any]:
        """Analyze the error message to determine error type and location."""
        analysis = {
            "error_type": "Unknown",
            "error_line": None,
            "error_column": None,
            "error_description": error_message,
            "suggested_fixes": []
        }
        
        # Extract error type
        if "SyntaxError" in error_message:
            analysis["error_type"] = "SyntaxError"
        elif "NameError" in error_message:
            analysis["error_type"] = "NameError"
        elif "ImportError" in error_message or "ModuleNotFoundError" in error_message:
            analysis["error_type"] = "ImportError"
        elif "IndentationError" in error_message:
            analysis["error_type"] = "IndentationError"
        elif "AttributeError" in error_message:
            analysis["error_type"] = "AttributeError"
        elif "TypeError" in error_message:
            analysis["error_type"] = "TypeError"
        elif "ValueError" in error_message:
            analysis["error_type"] = "ValueError"
        
        # Extract line number if available
        line_match = re.search(r"line (\d+)", error_message)
        if line_match:
            analysis["error_line"] = int(line_match.group(1))
            
        return analysis
    
    def _apply_pattern_fixes(self, code: str, error_message: str, error_type: str) -> Tuple[str, List[str], float]:
        """Apply pattern-based fixes for common errors."""
        rectified_code = code
        changes_made = []
        confidence = 0.0
        
        # Try to find and apply appropriate fix
        for pattern, fix_func in self.error_patterns.items():
            if pattern.lower() in error_message.lower() or pattern == error_type:
                try:
                    result = fix_func(code, error_message)
                    if result:
                        rectified_code = result.get("code", code)
                        changes_made.extend(result.get("changes", []))
                        confidence = result.get("confidence", 0.8)
                        break
                except Exception as e:
                    print(f"Error applying fix for {pattern}: {e}")
                    continue
        
        return rectified_code, changes_made, confidence
    
    def _fix_future_imports(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix __future__ imports that are not at the beginning of the file."""
        lines = code.split('\n')
        future_imports = []
        other_lines = []
        shebang = None
        
        # Separate future imports from other lines
        for i, line in enumerate(lines):
            stripped = line.strip()
            if i == 0 and line.startswith('#!'):
                shebang = line
            elif 'from __future__ import' in stripped:
                future_imports.append(line)
            else:
                other_lines.append(line)
        
        # Reconstruct code with future imports at the top
        rectified_lines = []
        if shebang:
            rectified_lines.append(shebang)
        rectified_lines.extend(future_imports)
        rectified_lines.extend(other_lines)
        
        return {
            "code": '\n'.join(rectified_lines),
            "changes": ["Moved __future__ imports to the beginning of the file"],
            "confidence": 0.95
        }
    
    def _analyze_syntax_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Analyze and fix syntax errors."""
        try:
            ast.parse(code)
            return {"code": code, "changes": [], "confidence": 0.0}
        except SyntaxError as e:
            # Common syntax error fixes
            if "invalid syntax" in str(e).lower():
                return self._fix_invalid_syntax(code, str(e))
            elif "unexpected indent" in str(e).lower():
                return self._fix_indentation_error(code, str(e))
        
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _fix_invalid_syntax(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix common invalid syntax issues."""
        lines = code.split('\n')
        changes = []
        
        # Fix missing colons in control structures
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith(('if ', 'elif ', 'else', 'for ', 'while ', 'def ', 'class ', 'try', 'except', 'finally', 'with ')) 
                and not stripped.endswith(':')):
                lines[i] = line + ':'
                changes.append(f"Added missing colon on line {i+1}")
        
        return {
            "code": '\n'.join(lines),
            "changes": changes,
            "confidence": 0.8 if changes else 0.0
        }
    
    def _fix_name_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix name errors by adding missing imports or variable definitions."""
        # Extract the undefined name
        match = re.search(r"name '([^']+)' is not defined", error_message)
        if not match:
            return {"code": code, "changes": [], "confidence": 0.0}
        
        undefined_name = match.group(1)
        changes = []
        
        # Common undefined names and their fixes
        common_imports = {
            'math': 'import math',
            'os': 'import os',
            'sys': 'import sys',
            'random': 'import random',
            'datetime': 'import datetime',
            're': 'import re',
            'json': 'import json',
            'time': 'import time',
            'collections': 'import collections',
            'itertools': 'import itertools',
            'numpy': 'import numpy as np',
            'pandas': 'import pandas as pd',
            'plt': 'import matplotlib.pyplot as plt',
        }
        
        if undefined_name in common_imports:
            import_line = common_imports[undefined_name]
            lines = code.split('\n')
            
            # Find where to insert the import
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('from __future__'):
                    insert_idx = i + 1
                elif line.strip().startswith('#') or not line.strip():
                    continue
                else:
                    break
            
            lines.insert(insert_idx, import_line)
            changes.append(f"Added missing import: {import_line}")
            
            return {
                "code": '\n'.join(lines),
                "changes": changes,
                "confidence": 0.9
            }
        
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _fix_import_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix import errors."""
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _fix_module_not_found(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix module not found errors."""
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _fix_indentation_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix indentation errors."""
        lines = code.split('\n')
        changes = []
        
        # Basic indentation fix - normalize to 4 spaces
        normalized_lines = []
        for line in lines:
            if line.strip():  # Non-empty line
                # Count leading spaces/tabs
                leading_whitespace = len(line) - len(line.lstrip())
                if '\t' in line[:leading_whitespace]:
                    # Replace tabs with 4 spaces
                    tabs = line[:leading_whitespace].count('\t')
                    spaces = line[:leading_whitespace].count(' ')
                    new_indent = '    ' * tabs + ' ' * spaces
                    normalized_lines.append(new_indent + line.lstrip())
                    changes.append(f"Normalized indentation on line {len(normalized_lines)}")
                else:
                    normalized_lines.append(line)
            else:
                normalized_lines.append(line)
        
        return {
            "code": '\n'.join(normalized_lines),
            "changes": changes,
            "confidence": 0.8 if changes else 0.0
        }
    
    def _fix_attribute_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix attribute errors."""
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _fix_type_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix type errors."""
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _fix_value_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix value errors."""
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _fix_key_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix key errors."""
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _fix_index_error(self, code: str, error_message: str) -> Dict[str, Any]:
        """Fix index errors."""
        return {"code": code, "changes": [], "confidence": 0.0}
    
    def _ai_rectify_code(self, code: str, error_message: str, error_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to rectify code when pattern-based fixes fail."""
        try:
            prompt = f"""
You are an expert Python developer. I have code that failed with an execution error. Please analyze the error and provide a corrected version of the code.

**Original Code:**
```python
{code}
```

**Error Message:**
{error_message}

**Error Analysis:**
- Error Type: {error_analysis.get('error_type', 'Unknown')}
- Error Line: {error_analysis.get('error_line', 'Unknown')}
- Description: {error_analysis.get('error_description', '')}

**Instructions:**
1. Identify the root cause of the error
2. Provide the corrected code
3. List the specific changes made
4. Ensure the code follows Python best practices and PEP8 standards

**Response Format:**
Please respond in the following JSON format:
{{
    "success": true/false,
    "code": "corrected code here",
    "changes": ["list of changes made"],
    "explanation": "explanation of the fixes",
    "confidence": 0.0-1.0
}}
"""
            
            response = self.model.invoke(prompt)
            
            # Try to parse JSON response
            import json
            try:
                result = json.loads(response.content)
                return result
            except json.JSONDecodeError:
                # If not JSON, extract code from markdown blocks
                code_match = re.search(r'```python\n(.*?)\n```', response.content, re.DOTALL)
                if code_match:
                    return {
                        "success": True,
                        "code": code_match.group(1).strip(),
                        "changes": ["AI-generated fixes applied"],
                        "confidence": 0.7
                    }
            
        except Exception as e:
            print(f"Error in AI rectification: {e}")
        
        return {"success": False, "code": code, "changes": [], "confidence": 0.0}


# Convenience function for direct usage
def rectify_code(code: str, error_message: str, execution_context: Dict[str, Any] = None) -> CodeRectificationResponse:
    """
    Convenience function to rectify code.
    
    Args:
        code: The original code that failed
        error_message: The error message from execution
        execution_context: Additional context about the execution environment
        
    Returns:
        CodeRectificationResponse with rectified code and analysis
    """
    rectifier = CodeRectifier()
    return rectifier.rectify_code(code, error_message, execution_context)