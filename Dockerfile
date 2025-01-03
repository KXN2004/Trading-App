FROM python:3.9-alpine

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt --no-cache-dir

EXPOSE 80

CMD ["fastapi", "run", "--port", "80"]

# Optionally, you can add 4 workers to the uvicorn server
# CMD ["fastapi", "run", "--workers", "4", "--port", "80"]
