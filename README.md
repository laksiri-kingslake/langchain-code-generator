# LangChain Code Generator

## Set-up

1. Set-up project and install dependencies
```bash
# initialize uv project
uv init

# create virtual environment and install dependencies
uc add autopep8 black fastapi jinja2 langchain-groq langchain-sandbox langgraph pydantic python-dotenv python-multipart uvicorn
```

2. Set environment variables
```bash
echo "GROQ_API_KEY='<your-groq-api-key>'" >> .env

```

3. Run
```bash
# run command-line interface
uv run main.py --prompt <your-prompt>
# or
script .venv/bin/activate
python main.py --prompt <your-prompt>

# run web interface
uv run app.py
# or
script .venv/bin/activate # if not already activated
python app.py
```

## References
1. [Build a Code Generator and Executor Agent Using LangGraph, LangChain Sandbox and Groq Kimi K2 Instruct: Context Engineering- Isolation Context](https://medium.com/the-ai-forum/build-a-code-generator-and-executor-agent-using-langgraph-langchain-sandbox-and-groq-kimi-k2-291a88e66e6f)