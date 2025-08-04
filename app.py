#!/usr/bin/env python3
"""
FastAPI Web Application for LangGraph Code Generator with GROQ Kimi K2
Provides a web interface for the code generation workflow.
"""

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.config import Config
from src.workflow import CodeGeneratorWorkflow

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="LangGraph Code Generator",
    description="Generate and execute Python code using GROQ Kimi K2 and LangChain Sandbox",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize the workflow
workflow = None
executor = ThreadPoolExecutor(max_workers=1)  # Single worker to prevent conflicts

def initialize_workflow():
    """Initialize the workflow instance."""
    global workflow
    try:
        config = Config()
        model = config.get_groq_model()
        workflow = CodeGeneratorWorkflow()
        print("✅ Workflow initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize workflow: {e}")
        return False

# Initialize workflow on startup
initialize_workflow()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
async def generate_code(
    prompt: str = Form(...),
    requirements: str = Form("")
):
    """Generate code based on user prompt."""
    print(f"📝 Received request: {prompt}")
    print(f"📋 Requirements: {requirements}")
    
    if not workflow:
        print("❌ Workflow not initialized")
        raise HTTPException(status_code=500, detail="Workflow not initialized")
    
    try:
        # Run workflow in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        def run_workflow():
            import threading
            # Mark thread as FastAPI context
            threading.current_thread()._fastapi_context = True
            
            print("🚀 Starting workflow execution")
            result = workflow.run(prompt, requirements if requirements else None)
            print(f"✅ Workflow completed with status: {result.get('workflow_status')}")
            return result
        
        # Execute workflow in a separate thread
        result = await loop.run_in_executor(executor, run_workflow)
        
        print("📤 Sending response to client")
        print(f"Response keys: {list(result.keys())}")
        
        # Process the result for web display
        response_data = {
            "success": result.get("workflow_status") == "completed",
            "final_result": result.get("final_result", "No result available"),
            "generated_code": result.get("rectified_code") or result.get("generated_code", ""),
            "execution_results": result.get("execution_results", {}),
            "syntax_errors": result.get("syntax_errors", []),
            "rectification_attempts": result.get("rectification_attempts", 0),
            "error_analysis": result.get("error_analysis", {}),
            "workflow_status": result.get("workflow_status", "unknown")
        }
        
        print(f"📊 Response data prepared: success={response_data['success']}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"❌ Error during code generation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Code generation failed: {str(e)}",
                "final_result": f"❌ Error: {str(e)}"
            }
        )


@app.get("/api/status")
async def api_status():
    """Get API status and configuration."""
    try:
        config = Config()
        model = config.get_groq_model()
        
        return {
            "status": "healthy",
            "workflow_initialized": workflow is not None,
            "groq_api_configured": bool(os.getenv("GROQ_API_KEY")),
            "model": "moonshotai/kimi-k2-instruct",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }


@app.get("/api/history")
async def get_history():
    """Get generation history (placeholder for future implementation)."""
    return {
        "history": [],
        "message": "History feature coming soon"
    }


@app.post("/api/test")
async def test_workflow():
    """Test the workflow with a simple request."""
    try:
        if not workflow:
            return {"success": False, "error": "Workflow not initialized"}
        
        test_prompt = "Create a simple function that adds two numbers"
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, workflow.run, test_prompt)
        
        return {
            "success": True,
            "test_prompt": test_prompt,
            "workflow_status": result.get("workflow_status"),
            "has_generated_code": bool(result.get("generated_code")),
            "has_execution_results": bool(result.get("execution_results")),
            "rectification_attempts": result.get("rectification_attempts", 0)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "LangGraph Code Generator",
        "version": "1.0.0",
        "timestamp": time.time()
    }


@app.get("/api/debug-workflow")
async def debug_workflow():
    """Debug endpoint to check workflow structure."""
    try:
        if not workflow:
            return {"error": "Workflow not initialized"}
        
        return {
            "workflow_initialized": True,
            "workflow_type": str(type(workflow)),
            "has_code_generator": hasattr(workflow, 'code_generator'),
            "has_syntax_checker": hasattr(workflow, 'syntax_checker'),
            "has_code_rectifier": hasattr(workflow, 'code_rectifier'),
            "has_code_executor": hasattr(workflow, 'code_executor'),
            "workflow_graph": hasattr(workflow, 'workflow')
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting LangGraph Code Generator Web Server")
    print("🌐 Access the application at: http://localhost:8000")
    print("📊 API documentation at: http://localhost:8000/docs")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )