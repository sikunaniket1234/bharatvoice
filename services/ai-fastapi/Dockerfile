FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /workspace
COPY services/ai-fastapi/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services/ai-fastapi ./services/ai-fastapi
ENV PYTHONPATH=/workspace/services/ai-fastapi
CMD ["uvicorn", "app.main:app", "--app-dir", "/workspace/services/ai-fastapi", "--host", "0.0.0.0", "--port", "8000"]
