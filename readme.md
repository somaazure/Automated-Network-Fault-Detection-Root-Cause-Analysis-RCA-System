# Automated Network Fault Detection & Root Cause Analysis (RCA)

<img width="532" height="852" alt="image" src="https://github.com/user-attachments/assets/594fcf12-4837-426d-8649-4315c3543e9b" />


Demo:
https://www.loom.com/share/ef9dbe155c6841f09fc0600ed324b441?sid=860d051f-7127-4285-ac09-304ff0ec6bdb

A practical system for analyzing telecom/network logs, classifying incident severity, executing simulated corrective actions, generating RCA reports, and surfacing insights via a Streamlit dashboard. It supports:

- **Streamlit UI** for RCA Management, Search (RAG over Pinecone), and Analytics
- **Agent flows** for severity classification and RCA generation
- **Slack notifications** for key incident lifecycle events
- **Pinecone** for semantic search over RCA reports
- **Kafka integration** for continuous log streaming and real-time processing

![Streamlit UI](./Streamlit_int.png)

---

## 1) Quick Start

- **Python**: 3.10 or newer is recommended
- **OS**: Windows (PowerShell) verified; Linux/macOS should work similarly

```powershell
# Clone
cd C:\Knowledge\GenAI2025
git clone https://github.com/somaazure/Automated-Network-Fault-Detection-Root-Cause-Analysis-RCA-System.git
cd Automated-Network-Fault-Detection-Root-Cause-Analysis-RCA-System

# (Optional) Create and activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create an .env file from the example
copy env_example .env
```

Then edit `.env` (see full list in Section 3). At minimum for Streamlit:
- `OPENAI_API_KEY=`
- `PINECONE_API_KEY=`, `PINECONE_INDEX=`, `PINECONE_NAMESPACE=` (index must exist)
- `SLACK_WEBHOOK_URL=` (optional; if not set, Slack is disabled)

Run the Streamlit app:
```powershell
streamlit run app.py
```

---

## 2) What’s Inside

- `app.py`: Streamlit dashboard with three tabs
  - **RCA Management**: processes `logs/` into `rca_reports/`, chunks and indexes in Pinecone
  - **RCA Search**: asks questions over the RCA knowledge base (RAG on Pinecone)
  - **Analytics**: simple charts summarizing RCA content
- `run_agents.py`: lightweight orchestrator using `agents/agent_orchestrator.py` for severity + RCA
- `network_fault_detection.py`: Azure AI multi‑agent flow with Slack notifications and simulated ops
- `storage/`
  - `log_processor.py`: converts raw logs to RCA summaries using OpenAI
  - `rca_vector_store.py`: Pinecone + OpenAI embeddings for indexing/search/answering
  - `analytics_engine.py`: helpers for analytics
- `agents/`
  - `agent_orchestrator.py`: Semantic Kernel setup and agent prompts wiring
  - `prompts.py`: instruction templates for severity and RCA agents
- `utils/slack_notifier.py`: simple Slack webhook notifier
- `logs/`: sample logs to process
- `rca_reports/`: generated RCA files (created at runtime)
- **Kafka Components:**
  - `kafka_producer.py`: streams logs from `logs/` to Kafka topic
  - `kafka_consumer.py`: consumes logs, writes to rolling files, triggers agent processing
  - `docker-compose.yml`: Kafka + ZooKeeper setup for local development

Architecture visual cues:

![Agent Orchestration](./Agent_PlayG.png)

![Base Agent](./BaseAgent.png)

![Pinecone Integration](./PineCone_Integration.png)

![Slack Notifications](./Slack_latest.png)

---

## 3) Environment Variables (.env)

Create a `.env` in the project root. The following are used across components:

- OpenAI (used by Streamlit RCA processing and RAG)
  - `OPENAI_API_KEY`

- Pinecone (index must pre-exist in your account)
  - `PINECONE_API_KEY`
  - `PINECONE_INDEX` (e.g., `rca-index`)
  - `PINECONE_NAMESPACE` (e.g., `rca-logs`)

- Slack (optional; used by agents and/or app where applicable)
  - `SLACK_WEBHOOK_URL` (incoming webhook URL)

- Azure OpenAI (required for `agents/agent_orchestrator.py`)
  - `AZURE_OPENAI_ENDPOINT` (e.g., `https://<resource>.openai.azure.com`)
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_DEPLOYMENT_NAME` (your chat model deployment, e.g., `gpt-4o-mini`)
  - `AZURE_OPENAI_API_VERSION` (optional; default `2024-07-01-preview`)

- Kafka (optional; for continuous log streaming)
  - `KAFKA_BROKER` (default: `localhost:9092`)
  - `KAFKA_TOPIC` (default: `network-logs`)
  - `STREAM_LOG_DIR` (default: `./logs/ingested`)
  - `DEBOUNCE_SEC` (default: `5`)
  - `SLEEP_BETWEEN_LINES` (default: `0.5`)
  - `LOOP` (default: `1`)

Notes:
- `storage/rca_vector_store.py` expects the Pinecone index to already exist. Create it in the Pinecone console (`https://app.pinecone.io`).
- Missing Slack webhook is OK; notifications will simply be skipped.
- Kafka integration requires Docker Desktop for local development.

---

## 4) Running the Streamlit Dashboard

1) Ensure `.env` is configured (Section 3) and dependencies installed.
2) Place sample logs (provided) in `logs/`.
3) Start the app:
```powershell
streamlit run app.py
```
4) In the sidebar, navigate between:
   - **📂 RCA Management**: Click once; it will:
     - Process new files from `logs/` into `rca_reports/`
     - Chunk and index reports into Pinecone
     - Preview the most recent RCA files
   - **🔍 RCA Search**: Ask questions over indexed RCA content (RAG powered by OpenAI + Pinecone)
   - **📊 Analytics**: View simple counts and charts derived from `rca_reports/`

Tip: If Pinecone is not configured or index missing, the Search tab will show errors/warnings. Configure `.env` and ensure your index exists.

---

## 4.1) Quick Demo Walkthrough

- Open the app and go to `📂 RCA Management` → process logs and index RCAs.
- Switch to `🔍 RCA Search` → ask a question like: "What were the top root causes?"
- Review `📊 Analytics` for simple counts.

## 5) Running the Agent Orchestrator (Simple)

This path uses the Semantic Kernel setup in `agents/agent_orchestrator.py`.

```powershell
python run_agents.py
```
What it does:
- Reads each `*.txt` file in `logs/`
- Classifies severity (SEVERITY_CLASSIFIER)
- Generates an RCA (ROOT_CAUSE_ANALYSIS)
- Saves RCA files to `rca_reports/`
- Sends Slack notifications if configured

Troubleshooting:
- If you see an error about missing Azure OpenAI config, ensure these are set in `.env`:
  - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT_NAME`

---

## 6) Running the Azure Multi‑Agent Flow (Advanced)

`network_fault_detection.py` uses Azure AI Agent Service with four agents and Slack notifications. You’ll need:
- Valid Azure OpenAI deployment and access
- Azure credentials on your machine (DefaultAzureCredential). On Windows, authenticate via:
```powershell
az login
```
Run:
```powershell
python network_fault_detection.py
```
Flow overview:
- USER provides the log file path (system iterates `logs/*.txt`)
- `INCIDENT_MANAGER` suggests one action (restart, reroute, QoS, scale, escalate, or no action)
- `NETWORK_OPS_ASSISTANT` executes simulated ops (appends to the same log)
- `SEVERITY_CLASSIFIER` returns P1/P2/P3 and triggers Slack notification
- `ROOT_CAUSE_ANALYSIS` writes a Markdown RCA into `rca_reports/` and signals completion

Common messages you might see:
- Slack enabled/disabled notice based on `SLACK_WEBHOOK_URL`
- Cooling down on API rate limits

---

## 7.1) Docker (Optional)

Run the app in Docker without installing Python locally.

1) Create a `Dockerfile` in the repo root (or copy-paste as needed):

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Streamlit runs on 8501 by default
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2) Build and run:

```bash
docker build -t network-rca:latest .
docker run --env-file .env -p 8501:8501 network-rca:latest
```

3) Open the UI at `http://localhost:8501`.

Notes:
- Mount local folders if you want to persist writes:
  - `-v %cd%/logs:/app/logs -v %cd%/rca_reports:/app/rca_reports` (PowerShell)
- Pinecone and OpenAI keys must be provided via `.env` or `-e` variables.

## 7) Pinecone Setup

- Create an index (e.g., name: `rca-index`, dimension matches OpenAI `text-embedding-3-small`)
- Put the values into `.env`:
  - `PINECONE_API_KEY`
  - `PINECONE_INDEX=rca-index`
  - `PINECONE_NAMESPACE=rca-logs`
- In `RCA Management`, re-run indexing to upsert vectors.

![Pinecone Integration](./PineCone_Integration.png)

---

## 8) Slack Setup (Optional)

- Create an Incoming Webhook in Slack and copy the URL
- Set `SLACK_WEBHOOK_URL` in `.env`
- You’ll receive notifications for severity classification, actions, and resolution (when applicable)

![Slack Notifications](./Slack_latest.png)

---

## 9) Testing the End‑to‑End Flow

- Ensure there are `.txt` logs under `logs/` (samples included)
- Path A (UI‑first):
  1. Run Streamlit, open **RCA Management** to generate/index RCAs
  2. Go to **RCA Search** and ask a question; verify sourced snippets
  3. View **Analytics** charts
- Path B (Agents‑first):
  1. Run `python run_agents.py`
  2. Confirm RCA files appear in `rca_reports/`
  3. Start Streamlit and use Search/Analytics on the generated RCAs
- Path C (Azure Multi‑Agent):
  1. `az login` then `python network_fault_detection.py`
  2. Watch console and Slack for status updates

---

## 10) Troubleshooting

- **Pinecone index does not exist**: The app will raise a message. Create it in the Pinecone console and set `PINECONE_INDEX` correctly.
- **OpenAI errors**: Ensure `OPENAI_API_KEY` is valid and you have access to the referenced models.
- **Azure OpenAI missing**: Provide `AZURE_OPENAI_*` in `.env` for agent flows.
- **Slack not configured**: Notifications are skipped; provide `SLACK_WEBHOOK_URL` to enable.
- **No RCA reports in Analytics/Search**: First generate them via **RCA Management** or by running the agents.

---

## 11) Kafka Integration (Continuous Log Streaming)

Enable real-time log processing with Kafka for continuous monitoring and automated RCA generation.

### 11.1) Prerequisites

- **Docker Desktop**: Install and start Docker Desktop
- **Python dependencies**: `pip install -r requirements.txt` (includes `kafka-python`)

### 11.2) Start Kafka Stack

**Option A: Docker Desktop UI**
1. Open Docker Desktop → Containers
2. Create → From compose file → select `docker-compose.yml` → Create
3. Verify both `zookeeper` and `kafka` show "Running" status

**Option B: Command Line**
```powershell
# Start Kafka + ZooKeeper
docker compose up -d

# Verify containers are running
docker compose ps

# Check Kafka logs
docker compose logs kafka --tail=50
```

**Expected output**: "Awaiting socket connections on 0.0.0.0:9092"

### 11.3) Run Kafka Consumer (Processes Incoming Logs)

Start the consumer first (keeps running):
```powershell
# Set environment variables
$env:KAFKA_BROKER="localhost:9092"
$env:KAFKA_TOPIC="network-logs"
$env:STREAM_LOG_DIR="./logs"          # or "./logs/ingested" (default)
$env:DEBOUNCE_SEC="5"                 # wait time after last line before processing

# Start consumer
python kafka_consumer.py
```

**What it does:**
- Consumes log messages from Kafka topic `network-logs`
- Appends lines to rolling files under `logs/` (or `logs/ingested/`)
- After `DEBOUNCE_SEC` of inactivity, triggers `AgentOrchestrator.process_network_incident()`
- Generates RCA files in `rca_reports/`

### 11.4) Run Kafka Producer (Streams Static Logs)

In a new terminal:
```powershell
# Set environment variables
$env:KAFKA_BROKER="localhost:9092"
$env:KAFKA_TOPIC="network-logs"
$env:LOGS_DIR="./logs"
$env:SLEEP_BETWEEN_LINES="0.5"        # throttle speed
$env:LOOP="1"                         # keep replaying

# Start producer
python kafka_producer.py
```

**What it does:**
- Reads `logs/*.txt` files line-by-line
- Sends each line as a JSON message to Kafka topic
- Continuously replays logs (set `LOOP=0` for single pass)

### 11.5) Monitor and Analyze

**Watch the flow:**
- Files grow in `logs/` (or `logs/ingested/`)
- Consumer terminal shows: `[Processed] stream_log1.txt | Severity: P2`
- New RCA files appear in `rca_reports/`

**Run Streamlit concurrently:**
```powershell
streamlit run app.py
```
- Go to **📂 RCA Management** → process/index new RCAs
- Use **🔍 RCA Search** → query indexed content
- View **📊 Analytics** → real-time dashboards

### 11.6) Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BROKER` | `localhost:9092` | Kafka broker address |
| `KAFKA_TOPIC` | `network-logs` | Topic name for log messages |
| `STREAM_LOG_DIR` | `./logs/ingested` | Where consumer writes rolling files |
| `DEBOUNCE_SEC` | `5` | Seconds to wait before processing file |
| `SLEEP_BETWEEN_LINES` | `0.5` | Producer delay between lines |
| `LOOP` | `1` | Producer replay mode (1=continuous, 0=single) |

### 11.7) Troubleshooting Kafka

**Consumer shows "NoBrokersAvailable":**
- Ensure Docker stack is running: `docker compose ps`
- Check Kafka logs: `docker compose logs kafka`
- Verify port 9092 is free: `netstat -ano | findstr :9092`

**Messages not flowing:**
- Confirm topic exists (auto-created on first producer send)
- Check environment variables match between producer/consumer
- Verify `KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092` in compose

**RCA not triggering:**
- Increase `DEBOUNCE_SEC` if lines arrive too frequently
- Check Azure OpenAI config for `AgentOrchestrator`
- Monitor consumer terminal for error messages

### 11.8) Stop Kafka Flow

```powershell
# Stop containers
docker compose down

# Close producer/consumer terminals
# (Ctrl+C in each terminal)
```

---

## 12) Repository Scripts At‑a‑Glance

- `streamlit run app.py` — UI for RCA Management, Search, and Analytics
- `python run_agents.py` — Simple agent pipeline
- `python network_fault_detection.py` — Azure multi‑agent pipeline with Slack
- `python kafka_producer.py` — Stream logs to Kafka
- `python kafka_consumer.py` — Consume logs and trigger RCA processing
- `docker compose up -d` — Start Kafka stack
- `docker compose down` — Stop Kafka stack

---

## 13) License

MIT (or your preferred license). Update as needed.


