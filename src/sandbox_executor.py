"""
Sandbox executor using LangChain's PyodideSandbox for safe Python code execution.
Based on: https://github.com/langchain-ai/langchain-sandbox/blob/main/examples/codeact_agent.py
"""

import asyncio
import time
import threading
from typing import Dict, Any, Optional
from langchain_sandbox import PyodideSandbox


class LangChainSandboxExecutor:
    """
    Executor that uses LangChain's PyodideSandbox for secure code execution.
    """
    
    def __init__(self, stateful: bool = True, allow_net: bool = True):
        """Initialize the PyodideSandbox."""
        self.sandbox = PyodideSandbox(
            stateful=stateful,
            allow_net=allow_net
        )
        # Session management for stateful execution
        self.session_bytes = None
        self.session_metadata = None
    
    async def _async_execute_code(self, code: str) -> Dict[str, Any]:
        """Execute code asynchronously using PyodideSandbox with session persistence."""
        try:
            start_time = time.time()
            
            # Execute code using the sandbox with session persistence
            if self.session_bytes and self.session_metadata:
                print("🔄 Using existing session for stateful execution")
                result = await self.sandbox.execute(
                    code, 
                    session_bytes=self.session_bytes,
                    session_metadata=self.session_metadata
                )
            else:
                print("🆕 Creating new session for stateful execution")
                result = await self.sandbox.execute(code)
            
            # Update session state for next execution
            if hasattr(result, 'session_bytes') and hasattr(result, 'session_metadata'):
                self.session_bytes = result.session_bytes
                self.session_metadata = result.session_metadata
                print(f"📦 Session updated: packages={result.session_metadata.get('packages', [])}")
            
            execution_time = time.time() - start_time
            
            # Convert the result to our format
            return {
                'success': result.status == 'success',
                'output': result.stdout or str(result.result) if result.result is not None else "Code executed successfully",
                'error': result.stderr if result.stderr else None,
                'execution_time': execution_time,
                'status': result.status,
                'result': result.result,
                'session_metadata': result.session_metadata if hasattr(result, 'session_metadata') else None,
                'packages_installed': result.session_metadata.get('packages', []) if hasattr(result, 'session_metadata') else []
            }
            
        except Exception as e:
            return {
                'success': False,
                'output': "",
                'error': f"PyodideSandbox execution error: {str(e)}",
                'execution_time': time.time() - start_time if 'start_time' in locals() else 0
            }
    
    def reset_session(self) -> None:
        """Reset the session to start fresh."""
        print("🔄 Resetting sandbox session")
        self.session_bytes = None
        self.session_metadata = None


class SafeCodeExecutor:
    """Fallback executor using restricted Python environment."""
    
    def __init__(self):
        self.restricted_functions = {
            'eval', 'exec', 'compile', '__import__', 'open', 'input',
            'raw_input', 'file', 'reload', 'vars', 'dir', 'globals',
            'locals', 'delattr', 'setattr', 'getattr', 'hasattr'
        }
    
    def execute_code(self, code: str) -> Dict[str, Any]:
        """Fallback execution using restricted environment."""
        start_time = time.time()
        
        # Basic safety check
        for restricted in self.restricted_functions:
            if restricted in code and not code.strip().startswith('#'):
                return {
                    'success': False,
                    'output': "",
                    'error': f"Restricted function '{restricted}' not allowed",
                    'execution_time': time.time() - start_time
                }
        
        try:
            # Create a restricted environment
            import io
            import sys
            from contextlib import redirect_stdout, redirect_stderr
            
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            restricted_globals = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'range': range,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'type': type,
                    'isinstance': isinstance,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                    'sorted': sorted,
                    'reversed': reversed,
                }
            }
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, restricted_globals)
            
            output = stdout_capture.getvalue()
            error = stderr_capture.getvalue()
            
            return {
                'success': len(error) == 0,
                'output': output if output else "Code executed successfully (no output)",
                'error': error if error else None,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'output': "",
                'error': f"Execution error: {str(e)}",
                'execution_time': time.time() - start_time
            }


# Global executor instance - try PyodideSandbox first, fallback to safe executor
try:
    sandbox_executor = LangChainSandboxExecutor()
    print("✅ Using LangChain PyodideSandbox for code execution")
except Exception as e:
    print(f"⚠️ PyodideSandbox not available, using fallback: {e}")
    sandbox_executor = SafeCodeExecutor()


def execute_code_async(code: str) -> Dict[str, Any]:
    """
    Execute code asynchronously, handling event loop context correctly.
    
    Args:
        code: Python code to execute
        
    Returns:
        Dict with success, output, error, execution_time
    """
    try:
        # Check if we're in an async context
        loop = asyncio.get_running_loop()
        
        # We're in an async context (like FastAPI), run in a separate thread
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                if hasattr(sandbox_executor, '_async_execute_code'):
                    return new_loop.run_until_complete(sandbox_executor._async_execute_code(code))
                else:
                    return sandbox_executor.execute_code(code)
            finally:
                new_loop.close()
        
        # Run in a separate thread to avoid event loop conflicts
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_new_loop)
            return future.result(timeout=30)
            
    except RuntimeError:
        # No running loop - we can use async directly
        if hasattr(sandbox_executor, '_async_execute_code'):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(sandbox_executor._async_execute_code(code))
            finally:
                loop.close()
        else:
            return sandbox_executor.execute_code(code)
    except Exception as e:
        return {
            'success': False,
            'output': "",
            'error': f"Execution setup error: {str(e)}",
            'execution_time': 0
        }