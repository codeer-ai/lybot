# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based CLI tool called "lybot" that serves as a comprehensive research assistant for querying Taiwan's Legislative Yuan (立法院) data. It uses Google's Gemini 2.5 Pro model via the pydantic-ai framework to provide conversational access to legislative information.

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

### Modular Design
The project is now organized into a modular structure:
```
lybot/
├── main.py           # Main application entry point
├── tools/            # All API tool implementations
│   ├── legislators.py    # Legislator-related tools
│   ├── bills.py         # Bill and proposal tools
│   ├── gazettes.py      # Gazette and voting record tools
│   ├── interpellations.py # Speech and interpellation tools
│   ├── meetings.py      # Meeting and attendance tools
│   └── analysis.py      # Advanced analysis tools
├── utils/            # Utility modules
│   └── constituency_mapper.py  # Constituency name normalization
└── prompts/          # Agent prompts and instructions
```

### Core Components

1. **AI Agent**: Uses Gemini 2.5 Pro model with comprehensive system prompt in Traditional Chinese
   - Supports Google's experimental "thinking mode" for enhanced reasoning
   - Structured prompts with role definition, core directives, and output formatting
2. **API Integration**: All API calls go to `https://ly.govapi.tw/v2/` endpoints
3. **Enhanced Tools** (40+ tools available):

   **Legislator Tools**:
   - `get_legislator_by_constituency`: Find legislators by electoral district with fuzzy matching
   - `get_legislator_details`: Get detailed legislator information including committees
   - `get_legislators_by_party`: List all legislators from a specific party
   - `get_legislator_proposed_bills`: Get bills proposed by a legislator
   - `get_legislator_meetings`: Get meeting attendance records
   - `get_party_seat_count`: Get party seat statistics
   - `get_legislator_committees`: Get committee memberships

   **Bill Tools**:
   - `search_bills`: Search bills with filters (keyword, proposer, type, session)
   - `get_bill_details`: Get detailed bill information
   - `get_bill_cosigners`: Extract co-signers from bill details
   - `analyze_legislator_bills`: Analyze legislator's bill proposals
   - `find_bills_by_keyword`: Find bills by keyword

   **Gazette and Voting Tools**:
   - `search_gazettes`: Search gazettes by date and keywords
   - `get_gazette_details`: Get gazette details with PDF links
   - `extract_voting_records_from_pdf`: Extract voting records from PDF
   - `find_voting_records_for_bill`: Find voting records for specific bills

   **Interpellation Tools**:
   - `search_interpellations`: Search interpellation records
   - `get_interpellation_details`: Get full interpellation content
   - `analyze_legislator_positions`: Analyze legislator positions on topics
   - `find_legislators_by_position`: Find legislators by their positions

   **Meeting and Attendance Tools**:
   - `calculate_attendance_rate`: Calculate legislator attendance rates
   - `compare_attendance_rates`: Compare multiple legislators' attendance
   - `get_session_info`: Get legislative session information
   - `get_party_attendance_statistics`: Get party-wide attendance stats

   **Analysis Tools**:
   - `analyze_party_statistics`: Comprehensive party performance analysis
   - `analyze_voting_alignment`: Analyze voting alignment with party
   - `find_cross_party_cooperation`: Find cross-party cooperation instances
   - `rank_legislators_by_activity`: Rank legislators by various metrics
   - `compare_legislators_performance`: Compare multiple legislators

### Technical Considerations

1. **Async Pattern**: Uses asyncio throughout for HTTP requests
2. **SSL Handling**: Custom SSL context for government PDF downloads (unverified)
3. **API Response Format**: Properly handles API responses with English keys (e.g., "legislators", "total")
4. **Constituency Mapping**: Smart normalization of constituency names (e.g., "台北市第七選區" → "臺北市第7選舉區")
5. **Language**: System prompts and user interaction in Traditional Chinese
6. **Term Support**: Currently optimized for 11th Legislative Yuan term
7. **PDF Processing**: Uses MarkItDown library for converting PDFs to markdown format
8. **Logging**: Integrated with loguru for structured logging

## Important Development Notes

1. **API Response Keys**: The API returns English keys like `legislators`, `bills`, `meets`, `total` instead of Chinese
2. **Constituency Format**: Official format is "臺北市第7選舉區" (Arabic numerals, not Chinese numerals)
3. **Party Names**: Use full party names (中國國民黨, 民主進步黨, 台灣民眾黨)
4. **Error Handling**: Enhanced error handling with fallback strategies
5. **Voting Records**: Can be extracted from gazette PDFs using the gazette tools
6. **Prompt Engineering**: The agent uses a structured prompt with:
   - Role definition and core directives
   - Think-first approach before tool execution
   - Structured output format with citations
   - Proactive suggestion capabilities
7. **Markdown Rendering**: Frontend includes specialized handling for:
   - Speaker names (bold text) with visual hierarchy
   - Enhanced list formatting with proper spacing
   - Blockquote styling for important content
   - Optimized Chinese typography

## Testing Status

- ✅ Basic legislator queries working
- ✅ Party statistics functional
- ✅ Constituency mapping tested
- ✅ Bill search operational
- ✅ Meeting/attendance tracking functional
- ⚠️ PDF voting record extraction needs real gazette testing
- ⚠️ Budget analysis features need document samples

## Web Frontend

### Frontend Architecture
The project now includes a modern web frontend built with:
- **Vite + React + TypeScript** for fast development and type safety
- **shadcn/ui** component library for polished UI components
- **Tailwind CSS v4** for modern styling with the latest features
- **FastAPI backend** with OpenAI-compatible API endpoints
- **React Markdown** with rehype-highlight for syntax highlighting
- **Custom markdown components** for Legislative Yuan transcript rendering

### Frontend Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # shadcn/ui components
│   │   ├── ChatInterface.tsx  # Main chat interface
│   │   └── ToolCallDisplay.tsx # Tool call visualization component
│   ├── lib/
│   │   ├── api.ts        # API client for backend communication
│   │   ├── types.ts      # TypeScript interfaces
│   │   └── utils.ts      # Utility functions
│   └── index.css         # Tailwind v4 CSS with design tokens
├── tailwind.config.js    # Tailwind v4 configuration
├── components.json       # shadcn/ui configuration
└── package.json          # Dependencies and scripts
```

### Development Commands
```bash
# Frontend development (in frontend/ directory)
npm install           # Install dependencies
npm run dev           # Start development server
npm run build         # Build for production

# Backend API server (in root directory)
python api.py         # Start FastAPI server on port 8000
```

### Technical Implementation

**Backend API (api.py)**:
- FastAPI server with OpenAI-compatible chat completions endpoint
- Streaming and non-streaming response support
- Session management for conversation history
- CORS enabled for frontend communication

**Frontend Features**:
- Modern chat interface with message bubbles
- Real-time streaming responses from AI with tool call visualization
- Dark/light theme toggle
- Professional Taiwan Legislative Yuan branding
- Responsive design with mobile support
- Type-safe API communication
- Enhanced markdown rendering for Legislative Yuan transcripts
- Specialized Chinese typography optimization

**Styling with Tailwind v4**:
- Uses `@import "tailwindcss"` for v4 syntax
- Modern color palette with HSL design tokens
- Glass morphism effects with backdrop blur
- Gradient buttons and message bubbles
- Smooth animations and micro-interactions
- Custom prose styling for transcript readability
- Optimized Chinese font stack and spacing

### Integration Notes

1. **API Compatibility**: Frontend communicates with FastAPI backend using OpenAI-compatible format
2. **Streaming**: Real-time message streaming using Server-Sent Events (SSE)
3. **Error Handling**: Graceful fallback from streaming to non-streaming mode
4. **Session Management**: Conversation history maintained on backend
5. **Modern UX**: Inspired by leading AI SaaS companies (OpenAI, Linear, Perplexity)

## Future Improvements to Consider

- Add comprehensive test suite with real API response fixtures
- Implement caching layer for frequently accessed data
- Add rate limiting for API calls
- Create batch operations for efficiency
- Add support for historical terms (not just 11th)
- Implement real-time session tracking
- Add webhook support for legislative updates
- Add user authentication and session persistence
- Implement message export functionality
- Add conversation search and history browsing