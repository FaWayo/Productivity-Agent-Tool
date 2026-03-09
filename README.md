# Productivity Pro — Personal AI Agent
MEST Tech Studio | Week 2 Assignment

## Overview
A personal productivity agent that manages your calendar, emails, notes,
and web searches through natural language. Built with PydanticAI + Streamlit.

## Features
- 4 core tools: Calendar, Email, Web Search, Notes
- Execution trace panel showing every tool call
- Human-in-the-loop approval for email sending
- Notes tool exposed as an MCP server
- Multi-turn conversation with memory

## Setup

### 1. Prerequisites
- Python 3.13+
- uv installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 2. Clone and install
    git clone https://github.com/YOUR_ORG/productivity-agent.git
    cd productivity-agent
    uv sync

### 3. Configure API keys
    cp .env.example .env
    # Edit .env and add your keys:
    # GEMINI_API_KEY=your_key_here
    # TAVILY_API_KEY=your_key_here (optional, falls back to mock)

### 4. Run the app
    uv run streamlit run main.py

### 5. Run the MCP server (optional, separate terminal)
    uv run python -m mcp_server.notes_server

## Team
- [Name 1] — Agent design & system prompt
- [Name 2] — Calendar & Email tools
- [Name 3] — Search & Notes tools
- [Name 4] — MCP server
- [Name 5] — UI & human-in-the-loop
