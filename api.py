"""FastAPI server for LyBot with OpenAI-compatible API."""

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
)
from pydantic_ai.usage import Usage
from sse_starlette.sse import EventSourceResponse

# Import the agent setup from main.py
from main import agent
from models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    ChatCompletionStreamResponse,
    ChatCompletionStreamResponseChoice,
    ChatCompletionStreamResponseDelta,
    FunctionCall,
    Message,
    ModelInfo,
    ModelListResponse,
    ToolCall,
)
from utils.analytics import capture
from utils.token_utils import token_count

# Store conversation sessions
sessions: Dict[str, List[ModelMessage]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    logger.info("Starting LyBot API server...")
    yield
    logger.info("Shutting down LyBot API server...")


app = FastAPI(
    title="LyBot API",
    description="OpenAI-compatible API for Taiwan Legislative Yuan research assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for web frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_session_history(session_id: str) -> List[ModelMessage]:
    """Get conversation history for a session."""
    return sessions.get(session_id, [])


def convert_tool_call_to_openai(tool_call: ToolCallPart) -> ToolCall:
    """Convert PydanticAI ToolCallPart to OpenAI ToolCall format."""
    return ToolCall(
        id=tool_call.tool_call_id,
        function=FunctionCall(
            name=tool_call.tool_name,
            arguments=json.dumps(tool_call.args)
            if isinstance(tool_call.args, dict)
            else str(tool_call.args),
        ),
    )


def extract_tool_calls_from_messages(messages: List[ModelMessage]) -> List[ToolCall]:
    """Extract tool calls from PydanticAI messages."""
    tool_calls = []
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                tool_calls.append(convert_tool_call_to_openai(part))
    return tool_calls


async def stream_response(
    agent: Agent,
    messages: List[Message],
    model: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """Stream response from the agent with real-time tool call support using iter()."""
    # Get existing session history
    message_history = get_session_history(session_id)

    # Extract the last user message as the prompt
    user_messages = [m for m in messages if m.role == "user"]
    if not user_messages:
        yield f"data: {json.dumps({'error': 'No user message found'})}\n\n"
        return

    prompt = user_messages[-1].content

    try:
        # Create initial response
        stream_id = f"chatcmpl-{int(time.time())}"

        # Send initial chunk
        initial_chunk = ChatCompletionStreamResponse(
            id=stream_id,
            model=model,
            choices=[
                ChatCompletionStreamResponseChoice(
                    index=0,
                    delta=ChatCompletionStreamResponseDelta(role="assistant"),
                    finish_reason=None,
                )
            ],
        )
        yield initial_chunk.model_dump_json()

        # Analytics: record start of streaming query
        capture(
            distinct_id=session_id,
            event="chat_query_start",
            properties={
                "prompt": prompt,
                "streaming": True,
            },
        )

        # Track state
        accumulated_text = ""
        tool_calls_sent = []

        final_usage: Usage | None = None

        # Run agent with iter() for fine-grained control
        async with agent.iter(prompt, message_history=message_history) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    # Model is generating response - stream text and tool calls
                    logger.debug("Processing ModelRequestNode")

                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent):
                                if isinstance(event.part, TextPart):
                                    # Starting text generation
                                    logger.debug(
                                        f"Starting text part: {event.part.content[:50]}..."
                                    )
                                    yield ChatCompletionStreamResponse(
                                        id=stream_id,
                                        model=model,
                                        choices=[
                                            ChatCompletionStreamResponseChoice(
                                                index=0,
                                                delta=ChatCompletionStreamResponseDelta(
                                                    role="assistant",
                                                    content=event.part.content,
                                                ),
                                                finish_reason=None,
                                            )
                                        ],
                                    ).model_dump_json()
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    # Stream text delta
                                    if event.delta.content_delta:
                                        chunk = ChatCompletionStreamResponse(
                                            id=stream_id,
                                            model=model,
                                            choices=[
                                                ChatCompletionStreamResponseChoice(
                                                    index=0,
                                                    delta=ChatCompletionStreamResponseDelta(
                                                        content=event.delta.content_delta
                                                    ),
                                                    finish_reason=None,
                                                )
                                            ],
                                        )
                                        yield chunk.model_dump_json()
                                        accumulated_text += event.delta.content_delta
                                elif isinstance(event.delta, ToolCallPartDelta):
                                    # Tool call delta - we'll handle complete tool calls in CallToolsNode
                                    logger.debug(f"Tool call delta: {event.delta}")

                elif Agent.is_call_tools_node(node):
                    # Model wants to call tools - stream tool call events
                    logger.debug("Processing CallToolsNode")

                    async with node.stream(run.ctx) as tools_stream:
                        async for event in tools_stream:
                            if isinstance(event, FunctionToolCallEvent):
                                # Convert to OpenAI format and stream immediately
                                tool_call = ToolCall(
                                    id=event.part.tool_call_id,
                                    function=FunctionCall(
                                        name=event.part.tool_name,
                                        arguments=json.dumps(event.part.args)
                                        if isinstance(event.part.args, dict)
                                        else str(event.part.args),
                                    ),
                                )
                                tool_calls_sent.append(tool_call)

                                # Send tool call chunk
                                tool_call_chunk = ChatCompletionStreamResponse(
                                    id=stream_id,
                                    model=model,
                                    choices=[
                                        ChatCompletionStreamResponseChoice(
                                            index=0,
                                            delta=ChatCompletionStreamResponseDelta(
                                                tool_calls=[tool_call]
                                            ),
                                            finish_reason=None,
                                        )
                                    ],
                                )
                                yield tool_call_chunk.model_dump_json()

                                logger.info(
                                    f"Streamed tool call: {event.part.tool_name}"
                                )

                            elif isinstance(event, FunctionToolResultEvent):
                                # Tool execution completed - stream the result
                                logger.debug(f"Tool {event.tool_call_id} completed")

                                # Create tool result message in OpenAI format
                                tool_result_chunk = ChatCompletionStreamResponse(
                                    id=stream_id,
                                    model=model,
                                    choices=[
                                        ChatCompletionStreamResponseChoice(
                                            index=0,
                                            delta=ChatCompletionStreamResponseDelta(
                                                role="tool",
                                                content=str(event.result.content),
                                                tool_call_id=event.tool_call_id,
                                            ),
                                            finish_reason=None,
                                        )
                                    ],
                                )
                                yield tool_result_chunk.model_dump_json()

                                # Analytics: record tool query + result
                                capture(
                                    distinct_id=session_id,
                                    event="tool_query",
                                    properties={
                                        "tool_call_id": event.tool_call_id,
                                        "result": str(event.result.content),
                                        "question": prompt,
                                        "response_tokens": token_count(
                                            str(event.result.content)
                                        ),
                                    },
                                )

                elif Agent.is_end_node(node):
                    # Agent run complete
                    logger.debug("Processing EndNode")
                    # Update session history
                    if hasattr(run, "result") and run.result:
                        sessions[session_id] = (
                            message_history + run.result.new_messages()
                        )
                    final_usage = run.usage()

        # Send final chunk
        final_finish_reason = "tool_calls" if tool_calls_sent else "stop"
        final_chunk = ChatCompletionStreamResponse(
            id=stream_id,
            model=model,
            choices=[
                ChatCompletionStreamResponseChoice(
                    index=0,
                    delta=ChatCompletionStreamResponseDelta(),
                    finish_reason=final_finish_reason,
                )
            ],
        )
        yield final_chunk.model_dump_json()

    except Exception as e:
        logger.error(f"Error in stream_response: {e}")
        error_chunk = {"error": {"message": str(e), "type": "internal_error"}}
        yield json.dumps(error_chunk)

    # Send final [DONE] message
    yield "[DONE]"

    # Emit analytics event (streaming)
    capture(
        distinct_id=session_id,
        event="chat_query_end",
        properties={
            "streaming": True,
            "tool_calls": len(tool_calls_sent),
            "request_tokens": final_usage.request_tokens if final_usage else -1,
            "response_tokens": final_usage.response_tokens if final_usage else -1,
            "total_tokens": final_usage.total_tokens if final_usage else -1,
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/v1/models")
async def list_models() -> ModelListResponse:
    """List available models."""
    models = [
        ModelInfo(
            id="lybot-gemini",
            created=int(time.time()),
            owned_by="lybot",
        )
    ]
    return ModelListResponse(data=models)


@app.post("/v1/chat/completions", response_model=None)
async def chat_completions(request: ChatCompletionRequest, http_request: Request):
    """OpenAI-compatible chat completions endpoint."""

    # Generate session ID from user or create new one
    session_id = request.user or f"session-{int(time.time())}"

    # Handle streaming response
    if request.stream:
        return EventSourceResponse(
            stream_response(agent, request.messages, request.model, session_id),
            media_type="text/event-stream",
        )

    # Handle non-streaming response
    try:
        # Get existing session history
        message_history = get_session_history(session_id)

        # Extract the last user message as the prompt
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")

        prompt = user_messages[-1].content

        # Run agent
        result = await agent.run(prompt, message_history=message_history)

        # Update session history using new_messages()
        new_messages = result.new_messages()
        sessions[session_id] = message_history + new_messages

        # Extract tool calls if any
        tool_calls = extract_tool_calls_from_messages(new_messages)

        # Create response with tool calls if present
        finish_reason = "tool_calls" if tool_calls else "stop"
        message = Message(
            role="assistant",
            content=result.output,
            tool_calls=tool_calls if tool_calls else None,
        )

        response = ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=message,
                    finish_reason=finish_reason,
                )
            ],
            usage={
                "prompt_tokens": -1,  # Would need token counting
                "completion_tokens": -1,
                "total_tokens": -1,
            },
        )

        return response

    except Exception as e:
        logger.error(f"Error in chat_completions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/sessions/clear")
async def clear_session(session_id: Optional[str] = None):
    """Clear conversation history for a session."""
    if session_id:
        if session_id in sessions:
            del sessions[session_id]
            return {"message": f"Session {session_id} cleared"}
        else:
            return {"message": f"Session {session_id} not found"}
    else:
        sessions.clear()
        return {"message": "All sessions cleared"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "LyBot API",
        "description": "OpenAI-compatible API for Taiwan Legislative Yuan research",
        "endpoints": {
            "/v1/chat/completions": "Chat completions (OpenAI-compatible)",
            "/v1/models": "List available models",
            "/health": "Health check",
            "/docs": "API documentation (Swagger UI)",
            "/redoc": "API documentation (ReDoc)",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        },
    )
