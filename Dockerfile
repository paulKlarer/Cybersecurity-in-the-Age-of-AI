FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for better security simulation
RUN useradd -m agent
USER agent

COPY .env .
COPY agent.py .
COPY questions.txt .
COPY solutions.txt .

ENTRYPOINT ["python", "agent.py"]
