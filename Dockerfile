FROM node:22-bookworm-slim AS ui-build
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/app \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    UI_URL=http://localhost \
    UI_PORT=8000
WORKDIR /app/backend
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r requirements.txt
COPY backend/ ./
COPY --from=ui-build /ui/dist/ ./static/
RUN useradd --create-home --uid 10001 app && mkdir -p /app/models
USER app
EXPOSE 8000
CMD ["python", "run.py"]
