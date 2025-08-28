# Variables
PYTHON=python
STREAMLIT=streamlit
APP=app.py
AGENTS=run_agents.py
ADVANCED=network_fault_detection.py
IMAGE_NAME=network-rca:latest

# Default target
help:
	@echo "Available targets:"
	@echo "  run           - Run Streamlit app"
	@echo "  agents        - Run simple agent orchestrator"
	@echo "  advanced      - Run Azure multi-agent flow"
	@echo "  build         - Install dependencies"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container (reads .env)"

run:
	$(STREAMLIT) run $(APP)

agents:
	$(PYTHON) $(AGENTS)

advanced:
	$(PYTHON) $(ADVANCED)

build:
	pip install -r requirements.txt

docker-build:
	docker build -t $(IMAGE_NAME) .

# Use --env-file .env and map ports/folders as needed
# On Windows PowerShell, volume mapping example: -v ${PWD}/logs:/app/logs

docker-run:
	docker run --env-file .env -p 8501:8501 $(IMAGE_NAME)