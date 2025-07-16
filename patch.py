from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from pydantic_ai import UnexpectedModelBehavior, _utils
from pydantic_ai._utils import number_to_datetime
from pydantic_ai.messages import ModelResponseStreamEvent
from pydantic_ai.models.openai import OpenAIStreamedResponse, _map_usage
from loguru import logger


@dataclass
class OpenAIStreamedResponsePatch(OpenAIStreamedResponse):  # type: ignore
    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:
        async for chunk in self._response:
            self._usage += _map_usage(chunk)

            try:
                choice = chunk.choices[0]
            except IndexError:
                continue

            # Handle the text part of the response
            if (delta := choice.delta) is not None and (
                content := delta.content
            ) is not None:
                yield self._parts_manager.handle_text_delta(
                    vendor_part_id="content", content=content
                )

            tool_calls = (
                choice.delta.tool_calls
                if choice.delta and choice.delta.tool_calls
                else []
            )
            for dtc in tool_calls:
                maybe_event = self._parts_manager.handle_tool_call_delta(
                    vendor_part_id=dtc.index,
                    tool_name=dtc.function and dtc.function.name,  # type: ignore
                    args=dtc.function and dtc.function.arguments,  # type: ignore
                    tool_call_id=dtc.id,
                )
                if maybe_event is not None:
                    yield maybe_event


async def _process_streamed_response_patched(  # type: ignore
    self, response: AsyncStream[ChatCompletionChunk]
) -> OpenAIStreamedResponse:
    """Process a streamed response, and prepare a streaming response to return."""
    peekable_response = _utils.PeekableAsyncStream(response)
    first_chunk = await peekable_response.peek()
    if isinstance(first_chunk, _utils.Unset):
        raise UnexpectedModelBehavior(  # pragma: no cover
            "Streamed response ended without content or tool calls"
        )

    return OpenAIStreamedResponsePatch(
        _model_name=self._model_name,
        _response=peekable_response,
        _timestamp=number_to_datetime(first_chunk.created),
    )


# === Gemini patch =============================================================
# Google Gemini sometimes yields streamed chunks whose candidate.content.parts is
# None (e.g. the final STOP chunk). The default implementation in
# `GeminiStreamedResponse._get_event_iterator` asserts that this field is not
# None, raising an AssertionError. We replace the iterator with a more tolerant
# version that simply skips such empty chunks.

try:
    # The import may fail if the user doesn’t have the Google / Gemini extras
    # installed – wrap it in a try/except to avoid breaking the rest of the
    # application in that case.
    from pydantic_ai.models.google import GeminiStreamedResponse, _metadata_as_usage  # type: ignore
    from pydantic_ai.messages import ThinkingPart  # noqa: F401 (import needed for isinstance checks)

    async def _get_event_iterator_gemini_patched(self):  # type: ignore
        """A patched version that tolerates empty parts in Gemini streamed chunks."""
        async for chunk in self._response:  # type: ignore[attr-defined]
            # Update usage from metadata (same as upstream implementation)
            self._usage = _metadata_as_usage(chunk)  # type: ignore[misc]

            # Skip if there are no candidates
            if not chunk.candidates:
                continue

            candidate = chunk.candidates[0]

            # Skip chunks without content
            if (
                candidate.content is None
                or getattr(candidate.content, "parts", None) is None
            ):
                # Gemini sometimes sends a final STOP chunk with no parts. Instead of skipping it
                # entirely (which can result in an empty `ModelResponse` later and crash the agent),
                # emit an empty text delta so that _parts_manager has at least one part recorded.
                logger.debug(
                    "Gemini: received empty chunk (likely final STOP); emitting noop text delta"
                )
                yield self._parts_manager.handle_text_delta(  # type: ignore[attr-defined]
                    vendor_part_id="content",
                    content="",
                )
                continue

            for part in candidate.content.parts:
                # Text part (may be normal content or a "thought")
                if part.text is not None:
                    if getattr(part, "thought", False):
                        yield self._parts_manager.handle_thinking_delta(  # type: ignore[attr-defined]
                            vendor_part_id="thinking", content=part.text
                        )
                    else:
                        yield self._parts_manager.handle_text_delta(  # type: ignore[attr-defined]
                            vendor_part_id="content", content=part.text
                        )
                # Function call (tool invocation)
                elif part.function_call is not None:
                    maybe_event = self._parts_manager.handle_tool_call_delta(  # type: ignore[attr-defined]
                        vendor_part_id=uuid4(),
                        tool_name=part.function_call.name,
                        args=part.function_call.args,
                        tool_call_id=part.function_call.id,
                    )
                    if maybe_event is not None:
                        yield maybe_event
                # Other part types (e.g. function_response) are currently ignored

    # Monkey-patch the method so all future Gemini streams use the tolerant iterator.
    GeminiStreamedResponse._get_event_iterator = _get_event_iterator_gemini_patched  # type: ignore[attr-defined]

except ModuleNotFoundError:
    # Gemini dependencies not installed; ignore.
    pass
