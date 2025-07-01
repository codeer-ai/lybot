export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'assistant' | 'tool';
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  toolCalls?: ToolCall[];
  isToolCallsComplete?: boolean;
  toolCallId?: string; // For tool messages
}

export interface FunctionCall {
  name: string;
  arguments: string;
}

export interface ToolCall {
  id: string;
  type: 'function';
  function: FunctionCall;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string | null;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  stream: boolean;
  user?: string;
  temperature?: number;
}

export interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: {
    index: number;
    message: {
      role: string;
      content: string;
      tool_calls?: ToolCall[];
    };
    finish_reason: string;
  }[];
}

export interface ChatCompletionStreamResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: {
    index: number;
    delta: {
      role?: string;
      content?: string;
      tool_calls?: ToolCall[];
      tool_call_id?: string;
    };
    finish_reason?: string;
  }[];
}