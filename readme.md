# 🚀 Automated Network Fault Detection & RCA System  

> AI-powered multi-agent system for **real-time telecom network fault detection**, **automated resolution**, and **root cause analysis (RCA)** using **Azure OpenAI**, **Semantic Kernel**, and **Slack notifications**.

---

## **📌 Project Overview**
Telecom networks generate **huge volumes of logs** across **RAN, Core, and Backhaul** layers, making manual monitoring **slow** and **error-prone**.  
This system automates the entire **incident lifecycle** — from **detection** to **remediation** to **RCA reporting** — using **Azure OpenAI** and **multi-agent orchestration** via **Semantic Kernel**.

Demo: https://www.loom.com/share/806f70fae81248b48ebc4ee8b45c6165?sid=50d207fe-5809-40ca-8a49-61f81950e316
---

## Slack Notifications:
<img width="1255" height="601" alt="image" src="https://github.com/user-attachments/assets/ad60e9aa-bd55-4dbc-af46-c728fea82fc0" />


## Terminal Log:
<img width="1339" height="633" alt="image" src="https://github.com/user-attachments/assets/a7536eb6-1b65-44cc-a415-19e1fae9ea22" />






## **⚡ Key Features**
- 🧠 **AI-Powered Incident Detection**  
   - Scans logs to identify anomalies and faults in real-time.  
- 🛠 **Automated Network Remediation**  
   - Executes actions like restarting nodes, rerouting traffic, adjusting QoS, and scaling capacity.  
- 📄 **RCA Report Generation**  
   - Produces detailed, Markdown-based **Root Cause Analysis** reports.  
- 🔔 **Slack Integration**  
   - Real-time notifications for incidents, actions, and resolution updates.  
- 🤖 **Multi-Agent Orchestration**  
   - Uses **Semantic Kernel** to coordinate decision-making between specialized AI agents.

---

## **🛠️ Tech Stack**
| **Component**         | **Technology Used** |
|-----------------------|----------------------|
| **Language**          | Python 3.11+         |
| **AI & LLM**          | Azure OpenAI Service |
| **Agent Orchestration** | Semantic Kernel     |
| **Notifications**     | Slack Webhooks       |
| **Report Generation** | Markdown RCA Reports |
| **Authentication**    | Azure Identity       |

---

## **📂 Project Structure**
```bash
├── logs/                   # Sample telecom logs (input)
├── rca_reports/            # RCA reports (Markdown)
├── network_fault_detection.py  # Main AI-powered script
├── README.md               # Project documentation
└── requirements.txt        # Dependencies
---

## ** Steps to run:**
git clone <reponame>
pip install -r requirements.txt
** Add the required info in .env
finally,Run the job:

python .\network_fault_detection.py 
