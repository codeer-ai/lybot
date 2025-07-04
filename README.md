# LyBot - 台灣立法院研究助理 🏛️

A comprehensive AI-powered research assistant for querying Taiwan's Legislative Yuan (立法院) data. Built with Google's Gemini 2.5 Pro model and the pydantic-ai framework, it provides conversational access to legislative information through CLI, web interface, and API.

🚀 **Live Demo**: [https://andydai.github.io/lybot/](https://andydai.github.io/lybot/) | **API**: [https://lybot-z5pc.onrender.com/v1](https://lybot-z5pc.onrender.com/v1)

## ✨ Features

- **40+ Specialized Tools** for comprehensive legislative data analysis
- **Traditional Chinese Interface** with natural language understanding
- **Modern Web UI** with real-time streaming responses and tool visualization
- **OpenAI-Compatible API** for seamless integration with existing tools
- **CLI Tool** for terminal-based interactions
- **Comprehensive Coverage**: 
  - 👥 Legislators: profiles, committees, attendance
  - 📜 Bills: search, details, co-signers, progress tracking
  - 🗳️ Voting Records: extraction from gazette PDFs
  - 💬 Interpellations: speeches and position analysis
  - 📊 Analytics: party statistics, cross-party cooperation, performance metrics

## Quick Start

### Prerequisites

- Python >=3.12
- Node.js 18+ (for web frontend)
- Google API Key for Gemini model

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/lybot.git
cd lybot
```

2. Install Python dependencies using `uv` (modern Python package manager):
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

3. Set up your API key and LLM MODEL:

```bash
# GOOGLE
export GEMINI_API_KEY="your-api-key-here"    
# OPENAI
export OPENAI_API_KEY="..."

# AZURE
export AZURE_OPENAI_ENDPOINT="..."
export AZURE_OPENAI_API_KEY="..."
export OPENAI_API_VERSION="..."

# LLM Model
export LLM_MODEL="azure:gpt-4.1"     # AZURE
export LLM_MODEL="google-gla:gemini-2.5-flash"   # GOOGLE   
export LLM_MODEL="openai:gpt-4o"  # OpenAI
```

4. Run
```
uv run python api.py
```

### Configuration

#### API URL Configuration

The LyBot API can be accessed locally or via the deployed instance:

**Default Production URL**: `https://lybot-z5pc.onrender.com/v1`

**For Frontend (Web UI)**:
```bash
# Create a .env file in the frontend directory
cd frontend
echo "VITE_API_BASE_URL=http://localhost:8000/v1" > .env

# Or use a custom deployment
echo "VITE_API_BASE_URL=https://your-custom-api.com/v1" > .env
```

**For Python Clients**:
```python
# Using OpenAI client
from openai import OpenAI

# Local development
client = OpenAI(
    base_url="http://localhost:8000/v1/",
    api_key="not-needed"  # No API key required for local
)

# Production deployment
client = OpenAI(
    base_url="https://lybot-z5pc.onrender.com/v1/",
    api_key="not-needed"
)
```

### Running the Application

#### Option 1: CLI Mode
```bash
python main.py
```

#### Option 2: Web Interface
1. Start the API server:
```bash
./run_api.sh
# or manually: uvicorn api:app --host 0.0.0.0 --port 8000
```

2. In a new terminal, start the frontend:
```bash
cd frontend
npm install  # first time only
./run_frontend.sh
# or manually: npm run dev
```

3. Open http://localhost:5173 in your browser

#### Option 3: API Client
```python
# See example_client.py for comprehensive examples
from openai import OpenAI

# Configure the client with your API URL
client = OpenAI(
    base_url="http://localhost:8000/v1/",  # Local development
    # base_url="https://lybot-z5pc.onrender.com/v1/",  # Production
    api_key="not-needed"  # No API key required
)

response = client.chat.completions.create(
    model="gemini-2.0-flash-thinking-exp-01-21",
    messages=[{"role": "user", "content": "誰是台北市第七選區的立委？"}]
)
print(response.choices[0].message.content)
```

## Available Tools

### Legislator Tools
- Search by constituency, party, or name
- Get detailed profiles and committee memberships
- Track proposed bills and meeting attendance
- Analyze party statistics

### Bill and Proposal Tools
- Search bills by keyword, proposer, or session
- Get bill details and co-signers
- Analyze legislator bill proposals
- Track bill progress

### Meeting and Voting Tools
- Search gazette records
- Extract voting records from PDFs
- Calculate attendance rates
- Compare legislator performance

### Analysis Tools
- Cross-party cooperation analysis
- Voting alignment tracking
- Activity ranking
- Performance comparisons

## 📁 Project Structure

```
lybot/
├── main.py              # CLI entry point with pydantic-ai agent
├── api.py               # FastAPI server with OpenAI-compatible endpoints
├── tools/               # Legislative data tools (40+ tools)
│   ├── legislators.py   # Legislator queries and profiles
│   ├── bills.py         # Bill search and analysis
│   ├── gazettes.py      # Gazette and voting records
│   ├── interpellations.py # Speech records
│   ├── meetings.py      # Meeting attendance
│   └── analysis.py      # Advanced analytics
├── prompts/             # Agent system prompts (Traditional Chinese)
├── models.py            # Data models and types
├── frontend/            # React + TypeScript web interface
│   ├── src/
│   │   ├── components/  # UI components (shadcn/ui)
│   │   └── lib/         # API client and utilities
│   └── dist/            # Production build
├── example_client.py    # API usage examples
├── run_api.sh          # API server launcher
└── pyproject.toml      # Project dependencies (managed by uv)
```

## 🛠️ Development

### Tech Stack

- **Backend**: Python 3.12+, FastAPI, pydantic-ai, asyncio
- **AI Model**: Google Gemini 2.5 Pro (with experimental thinking mode)
- **Frontend**: React, TypeScript, Vite, shadcn/ui, Tailwind CSS v4
- **Package Management**: uv (Python), npm (Node.js)
- **Data Source**: [Taiwan Legislative Yuan API](https://ly.govapi.tw/)

### Adding New Tools

1. Create a new tool in the `tools/` directory
2. Follow the existing async pattern with proper error handling
3. Register the tool in the agent configuration
4. Update type definitions if needed

### Frontend Development

```bash
cd frontend
npm run dev    # Development server with hot reload
npm run build  # Production build
npm run preview # Preview production build
```

**Key Features:**
- Real-time streaming with Server-Sent Events (SSE)
- Tool call visualization showing AI's reasoning process
- Responsive design with mobile support
- Dark/light theme toggle
- Enhanced markdown rendering for legislative transcripts

### API Development

The API follows OpenAI's chat completions format, making it compatible with most LLM client libraries.

**Endpoints:**
- `POST /v1/chat/completions` - Main chat endpoint
- `GET /v1/models` - List available models
- Full CORS support for web clients

## API Endpoints

- `POST /v1/chat/completions` - Main chat endpoint (streaming/non-streaming)
- `GET /v1/models` - List available models

## Configuration

- **GOOGLE_API_KEY**: Required for Gemini model access
- **Frontend**: Configure in `frontend/.env` if needed
- **API Port**: Default 8000, configurable in `run_api.sh`

## 💡 Examples

### CLI Usage
```bash
# Interactive mode
python main.py

# Example queries:
> 誰是台北市第七選區的立委？
> 民進黨有多少席次？
> 最近有哪些關於環保的法案？
> 分析國民黨和民進黨在勞工議題上的立場差異
> 找出跨黨派合作的法案
```

### Web Interface
- Modern chat interface with message history
- Real-time streaming responses with thinking process
- Tool call visualization showing data sources
- Professional Taiwan Legislative Yuan branding
- Dark/light theme support
- Optimized for Chinese typography

### API Usage Examples

**Using the Production Deployment**:
```python
# No local setup required - use the deployed API
from openai import OpenAI

client = OpenAI(
    base_url="https://lybot-z5pc.onrender.com/v1/",
    api_key="not-needed"
)

# Basic query
response = client.chat.completions.create(
    model="gemini-2.0-flash-thinking-exp-01-21",
    messages=[{"role": "user", "content": "民進黨有幾位立委？"}]
)
print(response.choices[0].message.content)

# Streaming example
for chunk in client.chat.completions.create(
    model="gemini-2.0-flash-thinking-exp-01-21",
    messages=[{"role": "user", "content": "分析立委出席率"}],
    stream=True
):
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

**Using httpx for direct API calls**:
```python
import httpx

# Production API
response = httpx.post(
    "https://lybot-z5pc.onrender.com/v1/chat/completions",
    json={
        "model": "gemini-2.0-flash-thinking-exp-01-21",
        "messages": [{"role": "user", "content": "誰是高雄市第一選區立委？"}],
        "stream": False
    }
)
print(response.json()["choices"][0]["message"]["content"])
```

## License

This project is licensed under the MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Guidelines
- Follow existing code patterns and async conventions
- Add tests for new features
- Update documentation as needed
- Use Traditional Chinese for user-facing strings
- Ensure compatibility with the 11th Legislative Yuan term data

## 🙏 Acknowledgments

- **Data Source**: [Taiwan Legislative Yuan Open Data](https://ly.govapi.tw/)
- **AI Model**: Google Gemini 2.5 Pro with experimental thinking mode
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/)
- **Framework**: [pydantic-ai](https://docs.pydantic.dev/ai/latest/) for structured AI interactions

## 🔗 Related Projects

- [Taiwan Legislative Yuan API Documentation](https://ly.govapi.tw/)
- [pydantic-ai Documentation](https://docs.pydantic.dev/ai/latest/)
- [Gemini API Documentation](https://ai.google.dev/)

---

<p align="center">Made with ❤️ for Taiwan's democratic transparency</p>