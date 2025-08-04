#!/usr/bin/env python3
"""
LangGraph Code Generator with GROQ Kimi K2 and Sandbox Execution
Main CLI interface for the code generation workflow.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from src.workflow import CodeGeneratorWorkflow


def print_banner():
    """Print the application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                 LangGraph Code Generator                     ║
║                with GROQ Kimi K2 & Sandbox                   ║
╠══════════════════════════════════════════════════════════════╣
║  Node 1: Code Generation (Kimi K2)                           ║
║  Node 2: Syntax Check & PEP8 (Black/Autopep8)                ║
║  Node 3: Code Rectification (AI + Pattern-based)             ║
║  Node 4: Code Execution (LangChain Sandbox)                  ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """Main entry point for the CLI application."""
    
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable is required")
        print("Please set your GROQ API key in the .env file")
        sys.exit(1)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate and execute Python code using LangGraph and GROQ Kimi K2"
    )
    parser.add_argument(
        "--prompt", 
        required=True,
        help="The code generation prompt/request"
    )
    parser.add_argument(
        "--requirements",
        help="Additional requirements or specifications"
    )
    parser.add_argument(
        "--verbose", 
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Print banner and startup info
    print_banner()
    
    # Check execution environment and initialize appropriate executor
    try:
        from src import sandbox_executor
        print("✅ Using LangChain PyodideSandbox for code execution")
    except ImportError as e:
        print(f"⚠️ Warning: Sandbox initialization issue: {e}")
    
    try:
        from src import fastapi_executor
        print("✅ FastAPI Safe Executor initialized")
    except ImportError as e:
        print(f"⚠️ Warning: FastAPI executor initialization issue: {e}")
    
    print(f"\n🚀 Processing request: {args.prompt}")
    print("\n" + "=" * 60)
    
    # Initialize and run the workflow
    try:
        workflow = CodeGeneratorWorkflow()
        
        print("🚀 Starting Code Generation Workflow")
        print(f"📝 User Prompt: {args.prompt}")
        
        if args.requirements:
            print(f"📋 Requirements: {args.requirements}")
        
        # Run the workflow
        result = workflow.run(args.prompt, args.requirements)
        
        print("✅ Workflow Complete")
        print("\n" + "=" * 60)
        
        # Display results
        if result.get("workflow_status") == "completed":
            print("✅ Code generation completed successfully!")
            print("\n" + result.get("final_result", "No result available"))
            
            # Additional debug info if verbose
            if args.verbose:
                print("\n" + "=" * 60)
                print("🔍 DEBUG INFORMATION")
                print(f"Final state keys: {list(result.keys())}")
                print(f"Workflow status: {result.get('workflow_status')}")
                print(f"Rectification attempts: {result.get('rectification_attempts', 0)}")
                if result.get('syntax_errors'):
                    print(f"Syntax errors: {result.get('syntax_errors')}")
                if result.get('execution_errors'):
                    print(f"Execution errors: {result.get('execution_errors')}")
                if result.get('execution_results'):
                    exec_results = result.get('execution_results')
                    print(f"Execution success: {exec_results.get('success', False)}")
                    if exec_results.get('error'):
                        print(f"Last execution error: {exec_results.get('error')}")
                    if exec_results.get('output'):
                        print(f"Last execution output: {exec_results.get('output')}")
                if result.get('error_analysis'):
                    error_analysis = result.get('error_analysis')
                    print(f"Error analysis: {error_analysis}")
                if result.get('rectified_code'):
                    print(f"Has rectified code: Yes ({len(result.get('rectified_code'))} chars)")
                else:
                    print("Has rectified code: No")
        else:
            print("❌ Code generation failed!")
            print(f"🔍 DEBUG: Actual workflow status = '{result.get('workflow_status')}'")
            print(f"🔍 DEBUG: Expected = 'completed'")
            if result.get("error_message"):
                print(f"Error: {result.get('error_message')}")
            if result.get("final_result"):
                print("\n" + result.get("final_result"))
            
            # Show debug info even when failed if verbose
            if args.verbose:
                print("\n" + "=" * 60)
                print("🔍 DEBUG INFORMATION (FAILED CASE)")
                print(f"Final state keys: {list(result.keys())}")
                print(f"Workflow status: {result.get('workflow_status')}")
                print(f"Rectification attempts: {result.get('rectification_attempts', 0)}")
                if result.get('execution_results'):
                    exec_results = result.get('execution_results')
                    print(f"Execution success: {exec_results.get('success', False)}")
                    print(f"Execution output: {exec_results.get('output', 'No output')}")
                    print(f"Execution error: {exec_results.get('error', 'No error')}")
                if result.get('generated_code'):
                    print(f"Has generated code: Yes ({len(result.get('generated_code'))} chars)")
                if result.get('rectified_code'):
                    print(f"Has rectified code: Yes ({len(result.get('rectified_code'))} chars)")
                else:
                    print("Has rectified code: No")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
