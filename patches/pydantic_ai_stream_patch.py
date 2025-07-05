"""Monkey patch pydantic_ai OpenAI streaming to ignore chunks with missing delta.

Importing this module installs the patch globally. Keep it lightweight—nothing outside of the
patch should be imported from here."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from openai import AsyncStream  # type: ignore
from openai.types.chat import ChatCompletionChunk  # type: ignore
from pydantic_ai import UnexpectedModelBehavior, _utils  # type: ignore
from pydantic_ai._utils import number_to_datetime  # type: ignore
from pydantic_ai.messages import ModelResponseStreamEvent  # type: ignore
from pydantic_ai.models.openai import (
    OpenAIModel,
    OpenAIStreamedResponse,
    _map_usage,
)  # type: ignore


@dataclass
class _OpenAIStreamedResponsePatched(OpenAIStreamedResponse):  # type: ignore
    """A safer streamed-response class that skips empty-delta chunks."""

    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:  # type: ignore
        async for chunk in self._response:  # type: ignore[attr-defined]
            # accumulate token usage even for malformed chunks
            self._usage += _map_usage(chunk)  # type: ignore

            # Some providers occasionally send an empty choices array
            try:
                choice = chunk.choices[0]
            except (AttributeError, IndexError):
                continue

            delta = getattr(choice, "delta", None)

            # Text delta
            if delta and (content := getattr(delta, "content", None)):
                yield self._parts_manager.handle_text_delta(  # type: ignore[attr-defined]
                    vendor_part_id="content",
                    content=content,
                )

            # Tool-call deltas
            tool_calls = delta.tool_calls if delta and getattr(delta, "tool_calls", None) else []  # type: ignore
            for dtc in tool_calls:
                maybe_event = self._parts_manager.handle_tool_call_delta(  # type: ignore[attr-defined]
                    vendor_part_id=dtc.index,
                    tool_name=dtc.function.name if dtc.function else None,  # type: ignore
                    args=dtc.function.arguments if dtc.function else None,  # type: ignore
                    tool_call_id=dtc.id,
                )
                if maybe_event is not None:
                    yield maybe_event


async def _process_streamed_response_patched(  # type: ignore
    self, response: AsyncStream[ChatCompletionChunk]
) -> _OpenAIStreamedResponsePatched:
    """Replacement for OpenAIModel._process_streamed_response with safer iterator."""

    peekable_response = _utils.PeekableAsyncStream(response)  # type: ignore
    first_chunk = await peekable_response.peek()
    if isinstance(first_chunk, _utils.Unset):  # type: ignore
        # No content at all: propagate the same exception type pydantic_ai expects
        raise UnexpectedModelBehavior("Streamed response ended without content or tool calls")

    return _OpenAIStreamedResponsePatched(
        _model_name=self._model_name,  # type: ignore
        _response=peekable_response,
        _timestamp=number_to_datetime(first_chunk.created),
    )


# --- apply patch on import ---
OpenAIModel._process_streamed_response = _process_streamed_response_patched  # type: ignore 