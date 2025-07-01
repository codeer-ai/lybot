import type { ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse, ChatMessage } from '@/lib/types';

const API_BASE_URL = 'http://localhost:8000/v1';

export class LyBotAPIClient {
  private sessionId: string;

  constructor() {
    this.sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  async chatCompletion(
    messages: ChatMessage[],
    options: {
      stream?: boolean;
      temperature?: number;
    } = {}
  ): Promise<ChatCompletionResponse> {
    const { stream = false, temperature = 0.7 } = options;

    const request: ChatCompletionRequest = {
      model: 'lybot-gemini',
      messages,
      stream,
      user: this.sessionId,
      temperature,
    };

    const response = await fetch(`${API_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async *chatCompletionStream(
    messages: ChatMessage[],
    options: {
      temperature?: number;
    } = {}
  ): AsyncGenerator<string, void, unknown> {
    const { temperature = 0.7 } = options;

    const request: ChatCompletionRequest = {
      model: 'lybot-gemini',
      messages,
      stream: true,
      user: this.sessionId,
      temperature,
    };

    const response = await fetch(`${API_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6); // Remove 'data: ' prefix
            
            if (data === '[DONE]') {
              return;
            }

            try {
              const parsed: ChatCompletionStreamResponse = JSON.parse(data);
              const content = parsed.choices[0]?.delta?.content;
              
              if (content) {
                yield content;
              }
            } catch (e) {
              // Skip invalid JSON lines
              console.warn('Failed to parse streaming response:', data);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async clearSession(): Promise<void> {
    await fetch(`${API_BASE_URL}/sessions/clear`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_id: this.sessionId }),
    });
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL.replace('/v1', '')}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Create a singleton instance
export const apiClient = new LyBotAPIClient();