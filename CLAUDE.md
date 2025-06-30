# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based CLI tool called "lybot" that serves as a research assistant for querying Taiwan's Legislative Yuan (立法院) data. It uses Google's Gemini 2.5 Pro model via the pydantic-ai framework to provide conversational access to legislative information.

## Development Setup and Commands

### Package Management
This project uses `uv` as the package manager (modern Python packaging tool).

```bash
# Install dependencies
uv sync

# Run the CLI application
python main.py

# Add new dependencies
uv add <package-name>
```

### Environment Requirements
- Python >=3.12
- Virtual environment is located at `.venv/`
- API key required: `GOOGLE_API_KEY` environment variable for Gemini model

## Architecture Overview

### Single Module Design
Currently, all functionality is contained in `main.py` which includes:
- CLI setup using `clai` framework
- AI agent configuration with `pydantic-ai`
- Tool definitions for accessing Legislative Yuan APIs
- Async HTTP client setup with custom SSL handling

### Core Components

1. **AI Agent**: Uses Gemini 2.5 Pro model with system prompt in Traditional Chinese
2. **API Integration**: All API calls go to `https://ly.govapi.tw/v2/` endpoints
3. **Tools Available**:
   - `get_legislators`: Retrieve legislator information (hardcoded to 11th term)
   - `get_ivod_transcript`: Get video transcripts from IVOD system
   - `search_ivod`: Search IVOD videos by legislator and query
   - `get_meeting_info`: Get meeting information with various filters
   - `get_meeting_info_by_id`: Get detailed meeting info by ID
   - `get_pdf_markdown`: Convert PDF documents to markdown (special SSL handling)

### Technical Considerations

1. **Async Pattern**: Uses asyncio throughout for HTTP requests
2. **SSL Handling**: Custom SSL context for government PDF downloads (unverified)
3. **Hardcoded Values**: Currently hardcoded to query 11th Legislative Yuan term
4. **Language**: System prompts and user interaction in Traditional Chinese

## Important Development Notes

1. **No Tests**: Currently no test suite exists. Follow the guideline to write tests before features.
2. **Single File**: All code is in `main.py` - consider modularization for future features.
3. **API Rate Limiting**: No rate limiting implemented for government API calls.
4. **Error Handling**: Basic error handling with user-friendly messages in Chinese.

## Future Improvements to Consider

- Add comprehensive test suite
- Modularize code into separate files (models, tools, api_client)
- Add configuration file for API endpoints and term numbers
- Implement proper logging configuration
- Add rate limiting for API calls
- Create proper documentation in README.md