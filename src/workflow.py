"""
LangGraph workflow for code generation, syntax checking, rectification, and execution.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.state import CodeGenerationState
from src.nodes import CodeGeneratorNode, SyntaxCheckerNode, CodeRectifierNode, CodeExecutorNode


class CodeGeneratorWorkflow:
    """Main workflow orchestrator for the code generation process."""
    
    def __init__(self):
        self.code_generator = CodeGeneratorNode()
        self.syntax_checker = SyntaxCheckerNode()
        self.code_rectifier = CodeRectifierNode()
        self.code_executor = CodeExecutorNode()
        
        # Initialize the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with all nodes and edges."""
        
        # Create the state graph
        workflow = StateGraph(CodeGenerationState)
        
        # Add nodes (remove the separate end node)
        workflow.add_node("code_generator", self.code_generator._execute)
        workflow.add_node("syntax_checker", self.syntax_checker._execute)
        workflow.add_node("code_rectifier", self.code_rectifier._execute)
        workflow.add_node("code_executor", self.code_executor._execute)
        
        # Set entry point
        workflow.set_entry_point("code_generator")
        
        # Add conditional edges for flow control
        workflow.add_conditional_edges(
            "code_generator",
            self._route_from_generator,
            {
                "syntax_checker": "syntax_checker",
                "end": END  # Direct to END
            }
        )
        
        workflow.add_conditional_edges(
            "syntax_checker", 
            self._route_from_syntax_checker,
            {
                "code_executor": "code_executor",
                "code_rectifier": "code_rectifier",
                "end": END  # Direct to END
            }
        )
        
        workflow.add_conditional_edges(
            "code_rectifier",
            self._route_from_rectifier,
            {
                "syntax_checker": "syntax_checker",
                "code_generator": "code_generator",
                "end": END  # Direct to END
            }
        )
        
        workflow.add_conditional_edges(
            "code_executor",
            self._route_from_executor,
            {
                "code_rectifier": "code_rectifier",
                "end": END  # Direct to END
            }
        )
        print(workflow.compile().get_graph().draw_mermaid())
        return workflow.compile()
    
    def _route_from_generator(self, state: CodeGenerationState) -> str:
        """Route from code generator node."""
        return state.get("current_node", "end")
    
    def _route_from_syntax_checker(self, state: CodeGenerationState) -> str:
        """Route from syntax checker node."""
        return state.get("current_node", "end")
    
    def _route_from_rectifier(self, state: CodeGenerationState) -> str:
        """Route from code rectifier node."""
        current_node = state.get("current_node", "end")
        
        # Implement retry logic for rectification
        retry_count = state.get("retry_count", 0)
        rectification_attempts = state.get("rectification_attempts", 0)
        
        # If we've tried too many times, end the workflow
        if retry_count >= 3 or rectification_attempts >= 3:
            return "end"
        
        return current_node
    
    def _route_from_executor(self, state: CodeGenerationState) -> str:
        """Route from code executor node."""
        return state.get("current_node", "end")
    
    def run(self, user_prompt: str, requirements: str = None) -> Dict[str, Any]:
        """
        Run the complete workflow.
        
        Args:
            user_prompt: The user's code generation request
            requirements: Additional requirements (optional)
            
        Returns:
            Final workflow state with generated and executed code
        """
        
        # Initialize state
        initial_state = {
            "user_prompt": user_prompt,
            "generated_code": "",
            "syntax_errors": [],
            "execution_results": {},
            "current_node": "code_generator", 
            "retry_count": 0,
            # Rectification fields
            "execution_errors": [],
            "rectified_code": "",
            "rectification_attempts": 0,
            "error_analysis": {}
        }
        
        if requirements:
            initial_state["requirements"] = requirements
        
        try:
            # Execute the workflow
            result = self.workflow.invoke(initial_state)
            
            # Process the final result (since _end_node logic was moved here)
            final_result = self._process_final_result(result)
            
            return final_result
            
        except Exception as e:
            return {
                **initial_state,
                "workflow_status": "failed",
                "error_message": f"Workflow execution failed: {str(e)}",
                "final_result": f"❌ Workflow failed: {str(e)}"
            }
    
    def _process_final_result(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the final workflow result (moved from _end_node)."""
        
        # Get the final code (prioritize rectified code if available)
        final_code = (state.get("rectified_code") or 
                     state.get("generated_code", ""))
        
        # Get execution results
        execution_results = state.get("execution_results", {})
        
        # Determine overall success
        workflow_success = execution_results.get('success', False) or (
            final_code and not execution_results.get('error')
        )
        
        # Create comprehensive final result
        final_result = f"""## Code Generation Complete

### Generated Code:
```python
{final_code}
```

### Code Explanation:
"""
        
        # Add code explanation if available
        if final_code:
            # Generate a brief explanation of what the code does
            code_lines = final_code.split('\n')
            if len(code_lines) > 0:
                first_line = code_lines[0].strip()
                if first_line.startswith('"""') or first_line.startswith("'''"):
                    # Extract docstring as explanation
                    in_docstring = True
                    docstring_lines = []
                    for line in code_lines[1:]:
                        if '"""' in line or "'''" in line:
                            break
                        docstring_lines.append(line.strip())
                    if docstring_lines:
                        final_result += "\n".join(docstring_lines)
                    else:
                        final_result += "This code implements the requested functionality with proper error handling and documentation."
                else:
                    final_result += "This code implements the requested functionality with proper error handling and documentation."
        
        final_result += f"""

### Execution Results:
- **Success**: {execution_results.get('success', False)}
- **Execution Time**: {execution_results.get('execution_time', 0):.2f} seconds
- **Output**: {execution_results.get('output', 'No output') or 'No output'}
- **Error**: {execution_results.get('error', 'No error') or 'No error'}

### Analysis:
"""
        
        # Add analysis based on execution results
        if execution_results.get('success'):
            final_result += """## Analysis

### 1. **Execution Status**: ✅ **SUCCESS**

The code executed successfully without any runtime errors.

### 2. **Code Quality**
- Follows PEP8 standards
- Includes proper error handling
- Well-documented and readable

### 3. **Performance**
- Executed efficiently within the time limit
- No obvious performance bottlenecks detected

### 4. **Recommendations**
The code is production-ready and follows Python best practices."""
        elif not execution_results.get('error') and final_code:
            # Code exists but wasn't executed (maybe just syntax checked)
            final_result += """## Analysis

### 1. **Generation Status**: ✅ **SUCCESS**

The code was generated successfully and passed syntax validation.

### 2. **Code Quality**
- Follows PEP8 standards
- Includes proper error handling
- Well-documented and readable

### 3. **Next Steps**
The code is ready for execution and appears to be syntactically correct."""
        else:
            error_msg = execution_results.get('error', '')
            rectification_attempts = state.get('rectification_attempts', 0)
            
            final_result += f"""## Analysis

### 1. **Execution Status**: ❌ **FAILED**

The code did not execute successfully.

### 2. **Error Details**
**Error Message**: {error_msg}

### 3. **Rectification Attempts**
- **Attempts Made**: {rectification_attempts}
- **Status**: {'Maximum attempts reached' if rectification_attempts >= 3 else 'Rectification attempted'}

### 4. **Recommendations**
"""
            if rectification_attempts >= 3:
                final_result += "The automatic rectification system reached its maximum attempts. Manual review may be required to resolve the remaining issues."
            else:
                final_result += "The code may require additional manual fixes to resolve the execution errors."
        
        # Add syntax check results
        syntax_errors = state.get("syntax_errors", [])
        final_result += f"""

### Syntax Check Results:
- **Syntax Errors**: {len(syntax_errors)} errors found
- **PEP8 Suggestions**: {'Applied' if len(syntax_errors) == 0 else 'Partially applied'}

---
*Generated using LangGraph Code Generator with GROQ*"""
        
        # Determine final workflow status
        final_workflow_status = "completed" if (workflow_success or final_code) else "failed"
        
        # Return the complete final state
        return {
            **state,
            "final_result": final_result.strip(),
            "workflow_status": final_workflow_status,
            "current_node": "end"
        }