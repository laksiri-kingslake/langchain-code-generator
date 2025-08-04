"""Configuration settings for the LangGraph Code Generator."""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from typing import Optional

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the application."""
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
        self.langsmith_tracing = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
        self.langsmith_project = os.getenv("LANGSMITH_PROJECT", "langgraph-code-generator")
        
        # Validate required API keys
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
    
    def get_groq_model(self, model_name: str = "moonshotai/kimi-k2-instruct", temperature: float = 0.1) -> ChatGroq:
        """
        Get a configured GROQ model instance.
        
        Primary Model - Kimi K2 (moonshotai/kimi-k2-instruct):
        ✅ Excels at agentic tasks, coding, and reasoning
        ✅ Supports tool calling capabilities
        ✅ 131K token context window (massive context)
        ✅ Mixture-of-Experts (MoE) with 32B activated parameters
        ✅ Fast inference optimized for reasoning models
        ⚠️ May struggle with very complex reasoning or unclear tool definitions
        
        Alternative GROQ models:
        - llama3-70b-8192: Llama 3 70B (excellent for complex tasks)
        - llama3-8b-8192: Llama 3 8B (faster, good for simpler tasks)
        - gemma-7b-it: Gemma 7B (alternative option)
        
        Reference: https://console.groq.com/docs/models
        """
        return ChatGroq(
            groq_api_key=self.groq_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=4096,
            timeout=60,
            max_retries=2
        )

# Global config instance
config = Config()