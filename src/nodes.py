"""Nodes for the LangGraph Code Generator workflow."""

import asyncio
import tempfile
import subprocess
import time
from typing import Dict, Any
from src.config import Config
from src.state import CodeGenerationState
from src.code_rectifier import CodeRectifier
from src import sandbox_executor, fastapi_executor


class CodeGeneratorNode:
    """Node for generating Python code using GROQ Kimi K2."""
    
    def __init__(self):
        self.config = Config()
        self.model = self.config.get_groq_model()
    
    def _execute(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Execute the code generation node."""
        print("🔧 Executing Code Generator (Iteration {})".format(state.get("retry_count", 0) + 1))
        
        prompt = f"""
You are an expert Python developer. Create high-quality, well-documented Python code based on the user's request.

**Requirements:**
- Follow PEP8 standards strictly
- Include proper type hints
- Add comprehensive docstrings
- Handle edge cases and errors gracefully
- Make the code production-ready and self-contained
- Include example usage and test cases when appropriate

**User Request:**
{state['user_prompt']}

**Important Guidelines:**
1. Start the code with proper imports (put __future__ imports at the very beginning if needed)
2. Create clean, readable, and efficient code
3. Include proper error handling
4. Add meaningful comments and documentation
5. Make sure all syntax is correct

Please provide only the Python code, no additional explanation:
"""
        
        try:
            response = self.model.invoke(prompt)
            generated_code = response.content.strip()
            
            # Remove code block markers if present
            if generated_code.startswith("```python"):
                generated_code = generated_code[9:]
            if generated_code.endswith("```"):
                generated_code = generated_code[:-3]
            
            generated_code = generated_code.strip()
            
            result = {
                "generated_code": generated_code,
                "current_node": "syntax_checker"
            }
            
            return {**state, **result}
            
        except Exception as e:
            return {
                **state,
                "execution_results": {
                    "success": False,
                    "error": f"Code generation failed: {str(e)}",
                    "output": "",
                    "execution_time": 0
                },
                "current_node": "end"
            }


class SyntaxCheckerNode:
    """Node for checking and correcting code syntax using Black, Autopep8, and Flake8."""
    
    def _execute(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Execute the syntax checking node."""
        print("🔍 Executing Syntax Checker")
        
        code = state.get("rectified_code") or state.get("generated_code", "")
        if not code:
            return {
                **state,
                "syntax_errors": ["No code to check"],
                "current_node": "end"
            }
        
        syntax_errors = []
        
        try:
            # Create temporary file for syntax checking
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Run Flake8 for syntax and style checking
            try:
                result = subprocess.run(
                    ['flake8', '--max-line-length=88', '--extend-ignore=E203,W503', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.stdout:
                    errors = result.stdout.strip().split('\n')
                    for error in errors:
                        if error.strip():
                            print(error)
                            syntax_errors.append(error)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Try to format with Black if no critical errors
            if not any("SyntaxError" in error for error in syntax_errors):
                try:
                    result = subprocess.run(
                        ['black', '--line-length=88', '--code', code],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0 and result.stdout:
                        code = result.stdout
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # Try autopep8 as fallback
                    try:
                        result = subprocess.run(
                            ['autopep8', '--aggressive', '--aggressive', '--max-line-length=88', '-'],
                            input=code,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode == 0 and result.stdout:
                            code = result.stdout
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass
            
            # Clean up
            import os
            try:
                os.unlink(temp_file)
            except:
                pass
            
            # Determine next node based on syntax errors
            if syntax_errors and any("SyntaxError" in error for error in syntax_errors):
                # Critical syntax errors - go to rectifier
                next_node = "code_rectifier"
            elif len(syntax_errors) == 0:
                # No errors - proceed to execution
                next_node = "code_executor"
            else:
                # Minor issues - proceed to execution but log warnings
                next_node = "code_executor"
            
            result = {
                "generated_code": code,
                "syntax_errors": syntax_errors,
                "current_node": next_node
            }
            
            return {**state, **result}
            
        except Exception as e:
            return {
                **state,
                "syntax_errors": [f"Syntax checking failed: {str(e)}"],
                "current_node": "code_rectifier"
            }


class CodeRectifierNode:
    """Node for rectifying code execution errors."""
    
    def __init__(self):
        self.rectifier = CodeRectifier()
    
    def _execute(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Execute the code rectification node."""
        print("🔧 Executing Code Rectifier")
        
        # Determine which code to rectify and what error occurred
        original_code = state.get("rectified_code") or state.get("generated_code", "")
        execution_results = state.get("execution_results", {})
        syntax_errors = state.get("syntax_errors", [])
        
        # Get error message from execution or syntax errors
        error_message = ""
        if execution_results.get("error"):
            error_message = execution_results["error"]
        elif syntax_errors:
            error_message = "; ".join(syntax_errors)
        
        if not error_message or not original_code:
            return {
                **state,
                "current_node": "end",
                "rectification_attempts": state.get("rectification_attempts", 0)
            }
        
        # Check rectification attempt limit
        attempts = state.get("rectification_attempts", 0)
        if attempts >= 3:
            print("⚠️ Maximum rectification attempts reached")
            return {
                **state,
                "current_node": "end",
                "execution_results": {
                    **execution_results,
                    "error": f"Maximum rectification attempts reached. Final error: {error_message}"
                }
            }
        
        try:
            # Rectify the code
            rectification_response = self.rectifier.rectify_code(
                original_code, 
                error_message,
                {"execution_context": "langgraph_workflow"}
            )
            
            if rectification_response.success and rectification_response.rectified_code:
                print(f"✅ Code rectified with confidence: {rectification_response.confidence_score:.2f}")
                print(f"🔄 Changes made: {', '.join(rectification_response.changes_made)}")
                
                result = {
                    "rectified_code": rectification_response.rectified_code,
                    "generated_code": rectification_response.rectified_code,  # Update generated_code too
                    "execution_errors": [error_message],
                    "rectification_attempts": attempts + 1,
                    "error_analysis": rectification_response.error_analysis,
                    "current_node": "syntax_checker"  # Re-check syntax after rectification
                }
                
                return {**state, **result}
            else:
                print("❌ Code rectification failed")
                return {
                    **state,
                    "current_node": "end",
                    "rectification_attempts": attempts + 1,
                    "execution_results": {
                        **execution_results,
                        "error": f"Rectification failed: {error_message}"
                    }
                }
                
        except Exception as e:
            print(f"❌ Error in code rectification: {e}")
            return {
                **state,
                "current_node": "end",
                "rectification_attempts": attempts + 1,
                "execution_results": {
                    **execution_results,
                    "error": f"Rectification error: {str(e)}"
                }
            }


class CodeExecutorNode:
    """Node for executing Python code in a sandbox environment."""
    
    def _execute(self, state: CodeGenerationState) -> Dict[str, Any]:
        """Execute the code execution node."""
        print("🚀 Executing Code in Sandbox")
        
        code = state.get("rectified_code") or state.get("generated_code", "")
        if not code:
            return {
                **state,
                "execution_results": {
                    "success": False,
                    "error": "No code to execute",
                    "output": "",
                    "execution_time": 0
                },
                "current_node": "end"
            }
        
        try:
            # Detect execution context and choose appropriate executor
            # Check for FastAPI context indicators
            import threading
            current_thread = threading.current_thread().name
            is_fastapi_context = (
                "ThreadPoolExecutor" in current_thread or 
                hasattr(threading.current_thread(), '_fastapi_context') or
                'executor' in current_thread.lower()
            )
            
            if is_fastapi_context:
                print("🌐 WEB CONTEXT DETECTED - Using FastAPI-compatible executor")
                
                # Use FastAPI-compatible executor
                start_time = time.time()
                result = fastapi_executor.execute_code(code)
                execution_time = time.time() - start_time
                
                execution_results = {
                    "success": result.get("success", False),
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "execution_time": execution_time
                }
                
            else:
                # Try to detect async context as backup
                try:
                    loop = asyncio.get_running_loop()
                    print("🌐 WEB CONTEXT DETECTED - Using FastAPI-compatible executor (async)")
                    
                    # Use FastAPI-compatible executor
                    start_time = time.time()
                    result = fastapi_executor.execute_code(code)
                    execution_time = time.time() - start_time
                    
                    execution_results = {
                        "success": result.get("success", False),
                        "output": result.get("output", ""),
                        "error": result.get("error", ""),
                        "execution_time": execution_time
                    }
                    
                except RuntimeError:
                    print("💻 CLI CONTEXT DETECTED - Using PyodideSandbox executor")
                    
                    # Use PyodideSandbox for CLI context
                    start_time = time.time()
                    result = sandbox_executor.execute_code_async(code)
                    execution_time = time.time() - start_time
                    
                    execution_results = {
                        "success": result.get("success", False),
                        "output": result.get("output", ""),
                        "error": result.get("error", ""),
                        "execution_time": execution_time
                    }
            
            # Determine next node based on execution results
            if not execution_results["success"] and execution_results.get("error"):
                # Execution failed - try rectification
                next_node = "code_rectifier"
            else:
                # Execution successful - end workflow
                next_node = "end"
            
            result = {
                "execution_results": execution_results,
                "current_node": next_node
            }
            
            return {**state, **result}
            
        except Exception as e:
            return {
                **state,
                "execution_results": {
                    "success": False,
                    "error": f"Execution error: {str(e)}",
                    "output": "",
                    "execution_time": 0
                },
                "current_node": "code_rectifier"  # Try rectification on unexpected errors
            }