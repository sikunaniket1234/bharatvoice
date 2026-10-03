FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /workspace

# build-essential is needed only by the ML layer, but it has to be installed in
# the same image. torch's Triton runtime compiles fused kernels at first use and
# raises "Failed to find C compiler. Please specify via CC environment variable"
# during generation on a slim image with no toolchain, which surfaced as a 502
# from the gateway rather than an obvious dependency error. gcc also lets
# IndicTransToolkit build from source if a wheel is ever unavailable.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# The machine-learning extras are opt-in. The contract, health and readiness
# endpoints all work without them, and the service reports itself not-ready, so
# a default build stays small and quick. Pass --build-arg INSTALL_ML=true to
# produce an inference-capable image.
#
# The PyTorch CUDA wheels come from the PyTorch index rather than PyPI. Change
# TORCH_INDEX_URL to cu126 or a CPU build if the host driver requires it.
ARG INSTALL_ML=false
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128

COPY services/ai-fastapi/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ai-fastapi/requirements-ml.txt ./requirements-ml.txt
RUN if [ "$INSTALL_ML" = "true" ]; then \
        pip install --no-cache-dir --extra-index-url "$TORCH_INDEX_URL" -r requirements-ml.txt; \
    else \
        echo "Skipping machine-learning extras; build with INSTALL_ML=true to enable inference."; \
    fi

COPY services/ai-fastapi ./services/ai-fastapi
ENV PYTHONPATH=/workspace/services/ai-fastapi
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "/workspace/services/ai-fastapi", "--host", "0.0.0.0", "--port", "8000"]