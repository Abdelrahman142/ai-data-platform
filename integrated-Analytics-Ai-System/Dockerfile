FROM python:3.13
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY . /app

RUN uv sync

EXPOSE 8000

# Let uv handle running the command in the correct environment
ENV PATH="/app/.venv/bin:$PATH"

# CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

CMD ["fastapi", "dev", "/app/api/main.py"]