from collections.abc import AsyncIterator
from dataclasses import dataclass

from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from pydantic_ai import UnexpectedModelBehavior, _utils
from pydantic_ai._utils import number_to_datetime
from pydantic_ai.messages import ModelResponseStreamEvent
from pydantic_ai.models.openai import OpenAIStreamedResponse, _map_usage


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
