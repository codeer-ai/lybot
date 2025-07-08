.PHONY: format
format:
	uv run ruff format .

lint:
	uv run ruff check .

run:
	uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload

