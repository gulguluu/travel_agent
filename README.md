# Travel Agent MCP Server

An intelligent travel planning agent built with the Model Context Protocol (MCP). Features AI-powered flight and hotel search with screenshot analysis, comprehensive travel tools, and conversational planning assistance.

## ✨ Key Features

- **AI-Powered Search**: Screenshot-based flight and hotel search with vision analysis
- **Conversational Planning**: Multi-turn conversations with memory persistence
- **Comprehensive Tools**: 29 specialized tools for flights, hotels, weather, transit, and more
- **Smart Assumptions**: Proactive planning with reasonable defaults
- **Performance Tracking**: Built-in monitoring and optimization
- **Modular Architecture**: Clean, extensible codebase

## 🛠️ Available Tools

**Flight Tools**: Search flights, flexible dates, route comparison, budget deals  
**Hotel Tools**: Search hotels, budget categories, landmark proximity, area comparison  
**Travel Intelligence**: Weather forecasts, Wikipedia research, currency conversion  
**Transportation**: Transit routes, driving directions, multi-modal planning  
**AI Services**: Travel advice, itinerary creation, sequential thinking  
**Utilities**: Memory storage, performance tracking, web search

## 🔧 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
```bash
# Required for AI features
export OPENROUTER_API_KEY=sk-or-...
export OPENAI_API_KEY=sk-...  # Alternative to OpenRouter
export OPENROUTER_MODEL=google/gemini-flash-1.5
```

### 3. Run the Server
```bash
python mcp_server.py
```

### 4. Run the Client
```bash
python travel_agent.py "Plan a trip to Tokyo in November"
```

## 🚀 Usage Examples

```bash
# Simple, proven working example
python travel_agent.py "Two weeks in November to South Korea from Portland"

# Other examples
python travel_agent.py "What's the weather in Paris?"
python travel_agent.py "Plan a 5-day honeymoon to Santorini in June, budget $4000"
python travel_agent.py "Business trip to London next month, need hotels near Canary Wharf"

# Interactive mode
python travel_agent.py
> Plan a weekend getaway from San Francisco
> I prefer luxury hotels and have a $2000 budget
```

## 🔧 Configuration

Set environment variables in `.env` file or export directly:

- `OPENROUTER_API_KEY` or `OPENAI_API_KEY`: Required for AI features
- `OPENROUTER_MODEL`: AI model selection (default: google/gemini-flash-1.5)
- `SERVER_HOST`: Server host (default: localhost)
- `SERVER_PORT`: Server port (default: 8000)

## 🤝 Contributing

The codebase follows a modular architecture with tools in `tools/`, utilities in `utils/`, and prompts in `prompts/`. Each tool is self-contained and uses shared utilities for consistency.
