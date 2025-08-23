import asyncio
import os
import textwrap
import json
import aiohttp
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings
from semantic_kernel.agents.strategies import (
    TerminationStrategy,
    SequentialSelectionStrategy,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_function_decorator import kernel_function

# Load environment variables from .env file
load_dotenv()

# =========================
# Slack Configuration
# =========================
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")  # Load from .env file

# =========================
# Agent Names & Prompts
# =========================
INCIDENT_MANAGER = "NETWORK_INCIDENT_MANAGER"
INCIDENT_MANAGER_INSTRUCTIONS = """
You are a Telecom Network Incident Manager.
You receive a path to a log file containing RAN/Core/Backhaul events and KPIs.

TASK:
- On every turn, read the log file using the available function.
- Decide ONE action from this set (exact strings):
  - Restart node {node_id}
  - Reroute traffic from {cell_id} to neighbor {neighbor_id}
  - Adjust QoS profile to {profile}
  - Scale capacity on {cell_id} by {percent}%
  - INCIDENT_MANAGER > No action needed.
  - Escalate issue.

WHEN TO PICK:
- "Restart node": node heartbeat missed, node down, radio process crash.
- "Reroute traffic": severe congestion on a cell; neighbor has headroom.
- "Adjust QoS profile": excessive packet loss or jitter; prioritize voice or critical slices.
- "Scale capacity": sustained >85% PRB utilization / throughput saturation for >10 minutes.
- "No action needed": KPIs normalized/already fixed (look for "stabilized", "recovered", "normalized").
- "Escalate issue": fiber cut, persistent failures after fix, or unknown root cause.

FORMAT:
- Read the log file (use the provided function).
- Respond ONLY with the chosen instruction line.
- ALWAYS prepend: "INCIDENT_MANAGER > {logfilepath} | "

RULES:
- Do NOT execute changes yourself.
- Do NOT call any execution functions.
"""

NETWORK_OPS_ASSISTANT = "NETWORK_OPS_ASSISTANT"
NETWORK_OPS_ASSISTANT_INSTRUCTIONS = """
You are a Network Operations Assistant.
Read the INCIDENT_MANAGER instruction and execute the mapped function.
Return only a short confirmation as "{function_response}".
If manager says "No action needed", reply exactly "No action needed."

RULES:
- Do NOT read logs yourself.
- Use the provided execution functions.
- ALWAYS prepend: "NETWORK_OPS_ASSISTANT > "
- After execution succeeds, emit a concise summary of action taken in the function response.
"""

SEVERITY_CLASSIFIER = "SEVERITY_CLASSIFIER"
SEVERITY_CLASSIFIER_INSTRUCTIONS = """
You are a Severity Classifier for Telecom incidents.
Read the log file using the provided function and classify the incident severity into:

- P1 (Critical): Complete outage, multiple nodes down, high revenue impact, emergency
  Examples: Core network failure, multiple eNB/gNB down, fiber cut affecting major area
- P2 (Major): Service degradation, affects many customers, significant performance impact
  Examples: Single node failure, congestion affecting >50% capacity, voice quality issues
- P3 (Minor): Isolated issue, early warning, minimal customer impact
  Examples: Single cell congestion, minor KPI degradation, preventive scaling

ANALYSIS CRITERIA:
- Customer impact scope (single cell vs multiple nodes vs region)
- Service availability (full outage vs degradation vs minor issues)
- KPI severity (>90% degradation = P1, 50-90% = P2, <50% = P3)
- Duration and persistence of issues

FORMAT:
- Read the log file using the available function
- Analyze the incident impact and scope
- Respond ONLY with the severity code: P1, P2, or P3
- ALWAYS prepend: "SEVERITY_CLASSIFIER > "

RULES:
- Do NOT execute any corrective actions
- Focus only on severity classification
"""

ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
ROOT_CAUSE_ANALYSIS_INSTRUCTIONS = """
You are the Root Cause Analysis (RCA) Agent.
When the Severity Classifier has assessed the incident and Network Operations Assistant has taken corrective action, you must:

1) Read the same log file using the provided function (this contains historical entries and appended ops results).
2) Look for the severity classification from the SEVERITY_CLASSIFIER in the conversation history.
3) Produce a Markdown RCA with the following sections and headings exactly:
## Incident Summary
## Incident Severity
## Impact Analysis
## Root Cause
## Corrective Actions Taken
## Preventive Measures
## Incident Timestamp

4) In the "Incident Severity" section, include the P1/P2/P3 classification and justify it based on the log analysis.
5) Save the RCA using the provided `save_rca_report(logfile, rca_markdown)` function.
6) Reply ONLY with this exact text when saved: "RCA_SAVED".

RULES:
- ALWAYS prepend: "RCA_AGENT > "
- Keep the RCA crisp and factual; no speculation when evidence is weak.
- Include severity classification and reasoning in the report.
"""

# =========================
# Paths
# =========================
SCRIPT_DIR = Path(__file__).parent
LOGS_DIR = SCRIPT_DIR / "logs"
RCA_DIR = SCRIPT_DIR / "rca_reports"
RCA_DIR.mkdir(exist_ok=True)

# =========================
# Slack Notification Helper
# =========================
class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
    
    async def send_notification(self, message: str, color: str = "good", title: str = None):
        """Send a notification to Slack using webhook"""
        if not self.enabled:
            print("Slack webhook not configured - skipping notification")
            return
        
        try:
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": title or "Network Operations Alert",
                        "text": message,
                        "footer": "Network Fault Detection System",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        print("✓ Slack notification sent successfully")
                    else:
                        print(f"✗ Slack notification failed: {response.status}")
                        
        except Exception as e:
            print(f"Error sending Slack notification: {e}")

    async def send_incident_detected(self, logfile: str, action: str, severity: str = None):
        """Send notification when incident is detected"""
        severity_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🟢"}.get(severity, "🚨")
        severity_text = f"\n**Severity:** {severity_emoji} {severity}" if severity else ""
        
        await self.send_notification(
            message=f"🚨 **Incident Detected**\n"
                   f"**Log File:** `{Path(logfile).name}`\n"
                   f"**Recommended Action:** {action}{severity_text}\n"
                   f"**Time:** {ts()}",
            color="danger" if severity == "P1" else "warning" if severity == "P2" else "good",
            title="Network Incident Detected"
        )
    
    async def send_action_taken(self, action: str, result: str):
        """Send notification when corrective action is taken"""
        await self.send_notification(
            message=f"🔧 **Corrective Action Taken**\n"
                   f"**Action:** {action}\n"
                   f"**Result:** {result}\n"
                   f"**Time:** {ts()}",
            color="warning",
            title="Network Action Executed"
        )
    
    async def send_severity_classification(self, logfile: str, severity: str):
        """Send notification when severity is classified"""
        severity_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🟢"}.get(severity, "❓")
        severity_desc = {
            "P1": "Critical - Complete outage or high revenue impact", 
            "P2": "Major - Service degradation affecting many customers",
            "P3": "Minor - Isolated issue or early warning"
        }.get(severity, "Unknown severity")
        
        color = "danger" if severity == "P1" else "warning" if severity == "P2" else "good"
        
        await self.send_notification(
            message=f"📊 **Incident Severity Classified**\n"
                   f"**Log File:** `{Path(logfile).name}`\n"
                   f"**Severity:** {severity_emoji} **{severity}** - {severity_desc}\n"
                   f"**Time:** {ts()}",
            color=color,
            title="Severity Assessment Completed"
        )
        """Send notification when RCA is completed"""
        await self.send_notification(
            message=f"📋 **RCA Report Generated**\n"
                   f"**Incident:** `{Path(logfile).name}`\n"
                   f"**RCA Report:** `{Path(rca_path).name}`\n"
                   f"**Time:** {ts()}",
            color="good",
            title="RCA Report Completed"
        )
    
    async def send_incident_resolved(self, logfile: str):
        """Send notification when incident is resolved"""
        await self.send_notification(
            message=f"✅ **Incident Resolved**\n"
                   f"**Log File:** `{Path(logfile).name}`\n"
                   f"**Status:** Network stabilized, no further action needed\n"
                   f"**Time:** {ts()}",
            color="good",
            title="Network Incident Resolved"
        )

# Global slack notifier instance
slack_notifier = SlackNotifier(SLACK_WEBHOOK_URL)

# Debug: Verify SlackNotifier methods are available
print("SlackNotifier methods:", [method for method in dir(slack_notifier) if not method.startswith('_')])
print("Has send_rca_completed:", hasattr(slack_notifier, 'send_rca_completed'))

# =========================
# MAIN
# =========================
async def main():
    # Clear console
    os.system('cls' if os.name=='nt' else 'clear')

    # Validate logs directory
    if not LOGS_DIR.exists():
        raise FileNotFoundError(f"Logs directory not found: {LOGS_DIR}")
    
    # Check Slack configuration
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URL not found in .env file or environment variables.")
        print("   Add SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL to your .env file")
        print("   Slack notifications will be disabled.")
    else:
        print("✓ Slack notifications enabled")
        print(f"✓ Webhook URL loaded: {SLACK_WEBHOOK_URL[:50]}...")  # Show first 50 chars for verification

    # Azure AI Agent settings (AZURE_OPENAI_* from env)
    ai_agent_settings = AzureAIAgentSettings()

    async with (
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ) as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):
        # Create agents in Azure AI Agent Service
        incident_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name=INCIDENT_MANAGER,
            instructions=INCIDENT_MANAGER_INSTRUCTIONS
        )
        agent_incident = AzureAIAgent(
            client=client,
            definition=incident_agent_definition,
            plugins=[LogFilePlugin()]  # read_log_file
        )

        ops_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name=NETWORK_OPS_ASSISTANT,
            instructions=NETWORK_OPS_ASSISTANT_INSTRUCTIONS
        )
        agent_ops = AzureAIAgent(
            client=client,
            definition=ops_agent_definition,
            plugins=[NetworkOpsPlugin()]  # executes actions + appends to logs
        )

        severity_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name=SEVERITY_CLASSIFIER,
            instructions=SEVERITY_CLASSIFIER_INSTRUCTIONS
        )
        agent_severity = AzureAIAgent(
            client=client,
            definition=severity_agent_definition,
            plugins=[LogFilePlugin()]  # read_log_file for severity assessment
        )

        rca_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name=ROOT_CAUSE_ANALYSIS,
            instructions=ROOT_CAUSE_ANALYSIS_INSTRUCTIONS
        )
        agent_rca = AzureAIAgent(
            client=client,
            definition=rca_agent_definition,
            plugins=[LogFilePlugin(), RCASaverPlugin()]  # read + save RCA
        )

        # Group chat with custom selection + termination
        chat = AgentGroupChat(
            agents=[agent_incident, agent_ops, agent_severity, agent_rca],
            termination_strategy=StabilizationOrSavedTerminationStrategy(
                agents=[agent_incident, agent_rca],
                maximum_iterations=16,
                automatic_reset=True
            ),
            selection_strategy=FourAgentTurnTaking(agents=[agent_incident, agent_ops, agent_severity, agent_rca]),
        )

        # Process each log file independently
        for filename in sorted(LOGS_DIR.glob("*.txt")):
            logfile_msg = ChatMessageContent(
                role=AuthorRole.USER,
                content=f"USER > {filename}"
            )
            print(f"\n=== Ready to process: {filename.name} ===\n")
            await chat.add_chat_message(logfile_msg)

            try:
                async for response in chat.invoke():  # multi-turn conversation
                    if response is None or not response.name:
                        continue
                    print(response.content)
            except Exception as e:
                print(f"Error during chat invocation: {e}")
                if "Rate limit is exceeded" in str(e):
                    print("Hit rate limit. Cooling down 60s...")
                    await asyncio.sleep(60)
                    continue
                else:
                    break

            # small pause to avoid TPM spikes
            await asyncio.sleep(2)

# =========================
# Selection Strategy (4-agent)
# =========================
class FourAgentTurnTaking(SequentialSelectionStrategy):
    """
    Enforces: USER → INCIDENT_MANAGER → NETWORK_OPS_ASSISTANT → SEVERITY_CLASSIFIER → ROOT_CAUSE_ANALYSIS → INCIDENT_MANAGER → …
    Logic:
      - After USER or RCA agent: INCIDENT_MANAGER
      - After INCIDENT_MANAGER: NETWORK_OPS_ASSISTANT
      - After NETWORK_OPS_ASSISTANT: SEVERITY_CLASSIFIER  
      - After SEVERITY_CLASSIFIER: ROOT_CAUSE_ANALYSIS
    """
    async def select_agent(self, agents, history):
        last = history[-1]
        if last.role == AuthorRole.USER or last.name == ROOT_CAUSE_ANALYSIS:
            target = INCIDENT_MANAGER
        elif last.name == INCIDENT_MANAGER:
            target = NETWORK_OPS_ASSISTANT
        elif last.name == NETWORK_OPS_ASSISTANT:
            target = SEVERITY_CLASSIFIER
        else:  # After SEVERITY_CLASSIFIER
            target = ROOT_CAUSE_ANALYSIS
        return next((a for a in agents if a.name == target), None)

# =========================
# Termination Strategy
# =========================
class StabilizationOrSavedTerminationStrategy(TerminationStrategy):
    """
    Stop when either:
      - The Incident Manager declares 'No action needed', OR
      - The RCA agent reports the RCA file saved (exact token 'RCA_SAVED').
    """
    async def should_agent_terminate(self, agent, history):
        last = history[-1].content.strip().lower()
        
        # Check if severity classifier responded and send notification
        if agent.name == SEVERITY_CLASSIFIER and last in ["p1", "p2", "p3"]:
            severity = last.upper()
            # Find the logfile from recent history
            for msg in reversed(history):
                if msg.role == AuthorRole.USER and "USER >" in msg.content:
                    logfile = msg.content.replace("USER > ", "").strip()
                    asyncio.create_task(slack_notifier.send_severity_classification(logfile, severity))
                    break
        
        # Check if incident resolved (no action needed)
        if "no action needed" in last:
            # Extract log file path from history to send resolved notification
            for msg in reversed(history):
                if msg.role == AuthorRole.USER and "USER >" in msg.content:
                    logfile = msg.content.replace("USER > ", "").strip()
                    await slack_notifier.send_incident_resolved(logfile)
                    break
        
        return (
            "no action needed" in last
            or "rca_saved" in last
            or "stabilized" in last
            or "recovered" in last
            or "normalized" in last
        )

# =========================
# Plugins
# =========================
class NetworkOpsPlugin:
    """
    Simulated network operations—writes confirmations back into the same log file.
    These functions are called ONLY by NETWORK_OPS_ASSISTANT.
    """

    def _append(self, filepath: str, content: str) -> None:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write("\n" + textwrap.dedent(content).strip())

    @kernel_function(description="Restart a network node")
    def restart_node(self, node_id: str = "", logfile: str = "") -> str:
        now = ts()
        entries = [
            f"[{now}] ALERT  Ops: Node {node_id} restart requested.",
            f"[{now}] INFO   Node-{node_id}: Restart initiated.",
            f"[{now}] INFO   Node-{node_id}: Services up. Heartbeat OK.",
            f"[{now}] INFO   KPIs: RRC setup success 98%, PRB util 54%, packet loss 0.3%. Stabilized."
        ]
        self._append(logfile, "\n".join(entries))
        
        result = f"Node {node_id} restarted and healthy."
        # Send Slack notification
        asyncio.create_task(slack_notifier.send_action_taken(f"Restart node {node_id}", result))
        return result

    @kernel_function(description="Reroute traffic from a congested cell to a neighbor")
    def reroute_traffic(self, cell_id: str = "", neighbor_id: str = "", logfile: str = "") -> str:
        now = ts()
        entries = [
            f"[{now}] ALERT  Ops: Rerouting traffic from {cell_id} → {neighbor_id}.",
            f"[{now}] INFO   Scheduler: eNB/NR handover preference updated.",
            f"[{now}] INFO   KPIs: {cell_id} PRB 88%→64%, {neighbor_id} PRB 52%→71%. Latency normalized."
        ]
        self._append(logfile, "\n".join(entries))
        
        result = f"Traffic rerouted from {cell_id} to {neighbor_id}."
        # Send Slack notification
        asyncio.create_task(slack_notifier.send_action_taken(f"Reroute traffic {cell_id} → {neighbor_id}", result))
        return result

    @kernel_function(description="Adjust QoS profile to stabilize voice/data")
    def adjust_qos(self, profile: str = "", logfile: str = "") -> str:
        now = ts()
        entries = [
            f"[{now}] ALERT  Ops: QoS profile switched to '{profile}'.",
            f"[{now}] INFO   PolicyCtrl: GBR bearers prioritized, jitter budget tuned.",
            f"[{now}] INFO   KPIs: MOS 4.3, jitter 9ms, loss 0.2%. Voice stabilized."
        ]
        self._append(logfile, "\n".join(entries))
        
        result = f"QoS adjusted to profile '{profile}'."
        # Send Slack notification
        asyncio.create_task(slack_notifier.send_action_taken(f"Adjust QoS to {profile}", result))
        return result

    @kernel_function(description="Scale capacity on a specific cell")
    def scale_capacity(self, cell_id: str = "", percent: int = 0, logfile: str = "") -> str:
        now = ts()
        entries = [
            f"[{now}] ALERT  Ops: Scaling capacity on {cell_id} by {percent}%.",
            f"[{now}] INFO   RAN: Carrier aggregation / beam configs optimized.",
            f"[{now}] INFO   KPIs: Throughput +{max(percent-3, 0)}%, PRB util 92%→71%. Stabilized."
        ]
        self._append(logfile, "\n".join(entries))
        
        result = f"Capacity scaled on {cell_id} by {percent}%."
        # Send Slack notification
        asyncio.create_task(slack_notifier.send_action_taken(f"Scale capacity on {cell_id} by {percent}%", result))
        return result

    @kernel_function(description="Escalate unresolved incident to human NOC")
    def escalate_issue(self, logfile: str = "") -> str:
        now = ts()
        entries = [
            f"[{now}] ALERT  Ops: Unable to fully remediate. Escalating to NOC L2.",
            f"[{now}] INFO   Ticket: Created incident with logs attached."
        ]
        self._append(logfile, "\n".join(entries))
        
        result = "Incident escalated to NOC."
        # Send urgent Slack notification for escalation
        asyncio.create_task(slack_notifier.send_notification(
            message=f"🚨 **URGENT: Incident Escalated**\n"
                   f"**Log File:** `{Path(logfile).name}`\n"
                   f"**Status:** Unable to auto-remediate - requires human intervention\n"
                   f"**Action:** NOC L2 ticket created\n"
                   f"**Time:** {ts()}",
            color="danger",
            title="Manual Intervention Required"
        ))
        return result

class LogFilePlugin:
    """Read a log file path and return its contents."""

    @kernel_function(description="Reads a log file and returns its contents")
    def read_log_file(self, filepath: str = "") -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Send incident detection notification if this is the first read (contains error/alert patterns)
        if any(keyword in content.lower() for keyword in ["error", "alert", "critical", "down", "failed"]):
            # Extract potential action from recent content for better notification
            lines = content.split('\n')
            recent_alerts = [line for line in lines[-10:] if any(k in line.lower() for k in ["error", "alert", "critical"])]
            
            if recent_alerts:
                asyncio.create_task(slack_notifier.send_incident_detected(filepath, "Analyzing incident..."))
        
        return content

class RCASaverPlugin:
    """Persist RCA Markdown to ./rca_reports directory."""

    @kernel_function(description="Save RCA markdown to disk")
    def save_rca_report(self, logfile: str = "", rca_markdown: str = "") -> str:
        log_name = Path(logfile).name.replace(".txt", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = RCA_DIR / f"RCA_{log_name}_{timestamp}.md"
        
        # Basic header added if missing
        if not rca_markdown.lstrip().startswith("#"):
            rca_markdown = f"# RCA Report - {log_name}\n\n" + rca_markdown
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(rca_markdown)
        
        # Debug: Check if method exists
        if hasattr(slack_notifier, 'send_rca_completed'):
            # Send RCA completion notification
            asyncio.create_task(slack_notifier.send_rca_completed(logfile, str(out_path)))
        else:
            print("Warning: SlackNotifier does not have send_rca_completed method")
            # List available methods for debugging
            print(f"Available methods: {[method for method in dir(slack_notifier) if not method.startswith('_')]}")
        
        return f"Saved: {out_path}"

# =========================
# Helpers
# =========================
def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =========================
# Entrypoint
# =========================
if __name__ == "__main__":
    asyncio.run(main())