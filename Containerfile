FROM python:3

RUN pip install uv
WORKDIR /app
COPY pyproject.toml uv.lock /app
RUN uv sync
COPY ./ ./
CMD ["uv", "run", "app.py"]
