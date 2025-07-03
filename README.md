# LyBot - Taiwan Legislative Yuan Research Assistant

A comprehensive AI-powered research assistant for querying Taiwan's Legislative Yuan (立法院) data. Built with Google's Gemini 2.5 Pro model, it provides conversational access to legislative information through both CLI and web interfaces.

## Features

- **40+ Specialized Tools** for legislative data analysis
- **Bilingual Support** with Traditional Chinese interface
- **Modern Web UI** with real-time streaming responses
- **OpenAI-Compatible API** for easy integration
- **CLI Tool** for command-line access
- **Comprehensive Coverage**: legislators, bills, meetings, voting records, interpellations, and more

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

2. Install Python dependencies using `uv`:
```bash
uv sync
```

3. Set up your Google API key:
```bash
export GOOGLE_API_KEY="your-api-key-here"
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

client = OpenAI(
    base_url="http://localhost:8000/v1/",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="gemini-2.0-flash-thinking-exp-01-21",
    messages=[{"role": "user", "content": "誰是台北市第七選區的立委？"}]
)
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

## Project Structure

```
lybot/
├── main.py              # CLI entry point
├── api.py               # FastAPI server
├── tools/               # Legislative data tools
├── frontend/            # React web interface
└── example_client.py    # API usage examples
```

## Development

### Adding New Tools

1. Create a new tool in the `tools/` directory
2. Follow the existing async pattern
3. Register the tool in the agent configuration

### Frontend Development

```bash
cd frontend
npm run dev    # Development server
npm run build  # Production build
```

### API Development

The API follows OpenAI's chat completions format, making it compatible with most LLM client libraries.

## API Endpoints

- `POST /v1/chat/completions` - Main chat endpoint (streaming/non-streaming)
- `GET /v1/models` - List available models

## Configuration

- **GOOGLE_API_KEY**: Required for Gemini model access
- **Frontend**: Configure in `frontend/.env` if needed
- **API Port**: Default 8000, configurable in `run_api.sh`

## Examples

### CLI Usage
```bash
# Interactive mode
python main.py

# Example queries:
> 誰是台北市第七選區的立委？
> 民進黨有多少席次？
> 最近有哪些關於環保的法案？
```

### Web Interface
- Modern chat interface with message history
- Real-time streaming responses
- Tool call visualization
- Dark/light theme support

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Data source: [Taiwan Legislative Yuan Open Data](https://ly.govapi.tw/)
- AI Model: Google Gemini 2.5 Pro
- UI Components: shadcn/ui