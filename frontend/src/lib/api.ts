import type { ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse, ChatMessage, ToolCall } from '@/lib/types';

// Use environment variable with fallback to production URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://lybot-z5pc.onrender.com/v1';
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
  ): AsyncGenerator<{ content?: string; tool_calls?: ToolCall[]; finish_reason?: string; role?: string; tool_call_id?: string }, void, unknown> {
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
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        // Decode the chunk and add to buffer
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Split by lines, but keep the last incomplete line in buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last incomplete line

        for (const line of lines) {
          const trimmedLine = line.trim();

          // Skip empty lines
          if (!trimmedLine) {
            continue;
          }

          if (trimmedLine.startsWith('data: ')) {
            const data = trimmedLine.slice(6).trim(); // Remove 'data: ' prefix

            if (data === '[DONE]') {
              return;
            }

            try {
              const parsed: ChatCompletionStreamResponse = JSON.parse(data);
              const delta = parsed.choices[0]?.delta;
              const finish_reason = parsed.choices[0]?.finish_reason;

              if (delta?.content || delta?.tool_calls || delta?.role || finish_reason) {
                yield {
                  content: delta?.content,
                  tool_calls: delta?.tool_calls,
                  finish_reason: finish_reason,
                  role: delta?.role,
                  tool_call_id: delta?.tool_call_id
                };
              }
            } catch (e) {
              // Skip invalid JSON lines silently
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