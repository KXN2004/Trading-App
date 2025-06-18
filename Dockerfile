FROM python:3.11-alpine AS app

# Change the Timezone to Asia/Kolkata.
ENV TZ=Asia/Kolkata
RUN apk add --no-cache tzdata && cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app
WORKDIR /app

# Install the application dependencies.
RUN uv sync --frozen --no-cache

# Run the application.
CMD [ "uv", "run", "app/main.py" ]

FROM python:3.11-alpine AS server

# Change the Timezone to Asia/Kolkata.
ENV TZ=Asia/Kolkata
RUN apk add --no-cache tzdata && cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app
WORKDIR /app

# Install the application dependencies.
RUN uv sync --frozen --no-cache

# Expose the application port.
EXPOSE 8000

# Run the application.
CMD [ "uv", "run", "fastapi", "run", "app/api.py" ]
