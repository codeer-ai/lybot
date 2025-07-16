import tiktoken


def _get_tiktoken_encoding(model: str = "o200k_base"):
    """Return a tiktoken encoding for the given model with a reasonable fallback."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to the cl100k_base encoding which is compatible with many models.
        return tiktoken.get_encoding("o200k_base")


def token_count(text: str | None, model: str = "o200k_base") -> int:
    """Count the number of tokens in the provided text for the specified model.

    This is a lightweight wrapper around tiktoken so we don't have to repeat
    the encoding logic everywhere in the codebase.
    """
    if text is None:
        return 0

    encoding = _get_tiktoken_encoding(model)
    return len(encoding.encode(text))
