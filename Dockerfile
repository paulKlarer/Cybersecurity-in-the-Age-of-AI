FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for better security simulation
RUN useradd -m agent
RUN chown -R agent:agent /app
USER agent

COPY --chown=agent:agent .env .
COPY --chown=agent:agent agent.py .
COPY --chown=agent:agent data/ ./data/
COPY --chown=agent:agent set_up_db.py .
RUN python set_up_db.py

ENTRYPOINT ["python", "agent.py"]
