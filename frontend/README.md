# LyBot Frontend

A modern, responsive web interface for the LyBot Taiwan Legislative Yuan research assistant.

## Features

- 🏛️ **Taiwan Legislative Yuan Branding** - Professional government-appropriate design
- 💬 **Real-time Chat Interface** - Streaming responses with live typing indicators
- 🌓 **Dark/Light Theme** - Toggle between themes with smooth transitions
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile devices
- ⚡ **Fast Performance** - Built with Vite for lightning-fast development and builds
- 🔌 **OpenAI-Compatible API** - Integrates with the LyBot FastAPI backend

## Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling and development server
- **Tailwind CSS** for styling with custom design system
- **Lucide React** for icons
- **OpenAI-compatible API client** for backend integration

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- LyBot API server running at `http://localhost:8000`

### Installation & Running

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   # or use the convenience script
   ./run_frontend.sh
   ```

3. **Open your browser:**
   - Frontend: http://localhost:5173 (or 5174 if 5173 is busy)
   - Make sure the API is running at: http://localhost:8000

### Building for Production

```bash
npm run build
npm run preview  # Preview production build
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                # Reusable UI components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   └── scroll-area.tsx
│   │   └── ChatInterface.tsx  # Main chat component
│   ├── lib/
│   │   ├── api.ts            # LyBot API client
│   │   ├── types.ts          # TypeScript type definitions
│   │   └── utils.ts          # Utility functions
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css             # Global styles with design system
├── tailwind.config.js        # Tailwind configuration
├── postcss.config.js         # PostCSS configuration
├── vite.config.ts            # Vite configuration
└── run_frontend.sh           # Convenience startup script
```

## Integration with LyBot API

The frontend integrates with the LyBot FastAPI backend using an OpenAI-compatible interface:

- **Non-streaming**: Standard request/response for simple queries
- **Streaming**: Real-time Server-Sent Events for live responses
- **Session management**: Maintains conversation context
- **Error handling**: Graceful fallbacks and user-friendly error messages

### API Configuration

The frontend expects the LyBot API to be running at `http://localhost:8000`. To change this, modify the `API_BASE_URL` in `src/lib/api.ts`.

## Usage Examples

### Sample Questions to Ask LyBot

Try these example queries in the chat interface:

- "請問臺北市第7選舉區的立委是誰？"
- "請分析民主進步黨在第11屆立法院的表現"
- "請查詢最近關於AI相關的法案"
- "請問台灣民眾黨有幾個立委？"
- "請幫我查詢柯文哲的質詢記錄"

## Deployment

### Static Hosting

Build the project and serve the `dist` folder:

```bash
npm run build
# Deploy the 'dist' folder to your static hosting service
```

### Supported Platforms

- Vercel, Netlify, GitHub Pages
- Any static file server or CDN

### Environment Configuration

For production deployment:

1. Update the `API_BASE_URL` in `src/lib/api.ts` to your production API
2. Ensure CORS is properly configured on the backend
3. Use HTTPS for both frontend and backend in production

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure the LyBot API is running at `http://localhost:8000`
   - Check the API health endpoint: `http://localhost:8000/health`
   - Verify CORS configuration in the backend

2. **Build Errors**
   - Clear node_modules and reinstall: `rm -rf node_modules && npm install`
   - Ensure you're using Node.js 18+

3. **Styling Issues**
   - Ensure Tailwind CSS is properly configured
   - Check that PostCSS plugins are correctly installed