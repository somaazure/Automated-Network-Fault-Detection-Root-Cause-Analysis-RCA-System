from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted

# ---------------------------
# Output PDF path
# ---------------------------
pdf_path = "Business_Functional_Requirements_Network_RCA_Final.pdf"

# Initialize PDF document
doc = SimpleDocTemplate(pdf_path, pagesize=A4)
styles = getSampleStyleSheet()
story = []

# ---------------------------
# Title & Subtitle
# ---------------------------
title_style = styles["Title"]
title_style.textColor = colors.HexColor("#0B3954")
story.append(Paragraph("Business & Functional Requirements Document", title_style))
story.append(Spacer(1, 12))

story.append(Paragraph(
    "Automated Network Fault Detection & Root Cause Analysis (RCA) System",
    styles["Heading2"]
))
story.append(Spacer(1, 20))

# ---------------------------
# Project Purpose
# ---------------------------
story.append(Paragraph("<b>Project Purpose</b>", styles["Heading3"]))
story.append(Paragraph(
    "The purpose of this project is to automate the detection of network faults and "
    "perform real-time root cause analysis (RCA) using AI-powered agents. "
    "This system aims to reduce downtime, improve operational efficiency, "
    "and enhance customer satisfaction by providing faster incident resolution.",
    styles["Normal"]
))
story.append(Spacer(1, 20))

# ---------------------------
# Technologies Used
# ---------------------------
story.append(Paragraph("<b>Technologies Used</b>", styles["Heading3"]))
tech_list = [
    "Azure OpenAI-powered multi-agent orchestration",
    "Azure Semantic Kernel for agent coordination",
    "Python 3.11+ for orchestration and automation",
    "Log analytics and AI-driven RCA",
    "Vector-based RCA report storage",
    "Azure Monitor & Application Insights integration"
]
for tech in tech_list:
    story.append(Paragraph(f"• {tech}", styles["Normal"]))
story.append(Spacer(1, 20))

# ---------------------------
# Business Requirements
# ---------------------------
story.append(Paragraph("<b>Business Requirements</b>", styles["Heading3"]))
business_reqs = [
    "Automate detection of network faults in real-time to reduce downtime.",
    "Provide early alerts to network operations teams for faster response.",
    "Leverage AI agents to analyze logs and pinpoint root causes of failures.",
    "Improve operational efficiency by reducing manual troubleshooting.",
    "Enable data-driven decisions based on historical incident patterns.",
    "Ensure high system availability and improve customer satisfaction.",
    "Integrate seamlessly with existing network monitoring and ticketing systems.",
    "Maintain comprehensive RCA reports for compliance and audit purposes.",
    "Facilitate predictive maintenance using AI-driven insights.",
    "Scale to support increasing network traffic and complex fault patterns."
]
for req in business_reqs:
    story.append(Paragraph(f"• {req}", styles["Normal"]))
story.append(Spacer(1, 20))

# ---------------------------
# Functional Requirements
# ---------------------------
story.append(Paragraph("<b>Functional Requirements</b>", styles["Heading3"]))
functional_reqs = [
    "System must parse and analyze incoming log files from multiple network sources.",
    "Detect anomalies and potential network faults using AI-powered agents.",
    "Trigger an Incident Manager Agent to assess issue severity and escalate if needed.",
    "Forward relevant logs to the Root Cause Analysis Agent for deeper investigation.",
    "Use Network Ops Agent to simulate and suggest corrective actions.",
    "Save RCA reports automatically using RCA Saver Plugin.",
    "Support integration with APIs for log ingestion and incident resolution.",
    "Maintain an audit trail of all incidents, RCA results, and remediation steps.",
    "Provide configurable alerting thresholds and escalation policies.",
    "Ensure system resilience and handle concurrent log streams efficiently."
]
for req in functional_reqs:
    story.append(Paragraph(f"• {req}", styles["Normal"]))
story.append(Spacer(1, 20))

# ---------------------------
# Agent & Plugin Mapping Table
# ---------------------------
story.append(Paragraph("<b>Agent & Plugin Mapping</b>", styles["Heading3"]))
table_data = [
    ["Agent / Plugin", "Role / Functionality"],
    ["Incident Manager Agent", "Scans incoming logs, detects incidents, and initiates escalation."],
    ["Root Cause Analysis Agent", "Performs deep RCA by correlating logs and identifying failure patterns."],
    ["Network Ops Agent", "Suggests corrective actions and simulates fixes for identified issues."],
    ["LogFilePlugin", "Handles reading and parsing of incoming log files."],
    ["NetworkOpsPlugin", "Interfaces with network systems to simulate resolutions."],
    ["RCASaverPlugin", "Saves RCA reports to persistent storage for auditing."]
]
table = Table(table_data, colWidths=[200, 330])
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3954")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 12),
    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)
]))
story.append(table)
story.append(Spacer(1, 20))

# ---------------------------
# System Architecture Diagram (Perfectly Aligned ASCII)
# ---------------------------
story.append(Paragraph("<b>System Architecture Overview</b>", styles["Heading3"]))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "The diagram below represents the end-to-end flow of the Automated Network Fault Detection & RCA System:",
    styles["Normal"]
))
story.append(Spacer(1, 12))

ascii_diagram = """
 +------------------+       +---------------------------+       +------------------+
 |   Log Sources    | -----> | LogFilePlugin (Parser)   | --->  | Incident Manager |
 +------------------+       +---------------------------+       +------------------+
                                                                            |
                                                                            v
                                                            +-------------------------------+
                                                            | Root Cause Analysis Agent     |
                                                            +-------------------------------+
                                                                            |
                                                                            v
                                                            +-------------------------------+
                                                            | Network Ops Agent             |
                                                            | (Simulates Fixes)             |
                                                            +-------------------------------+
                                                                            |
                                                                            v
                                                            +-------------------------------+
                                                            | RCA Saver Plugin              |
                                                            | (Stores RCA Reports)          |
                                                            +-------------------------------+
"""
story.append(Preformatted(ascii_diagram, styles["Code"]))
story.append(Spacer(1, 20))

# ---------------------------
# Non-functional Requirements
# ---------------------------
story.append(Paragraph("<b>Non-Functional Requirements</b>", styles["Heading3"]))
non_func_reqs = [
    "System should handle at least 10,000 logs per minute with minimal latency.",
    "Ensure 99.95% uptime for production deployment.",
    "Implement secure log handling and encrypted RCA report storage.",
    "Provide horizontal scalability to accommodate growing network complexity.",
    "Support observability and monitoring with integrated dashboards.",
    "Maintain role-based access control for authorized users only.",
    "Ensure GDPR and compliance readiness for audit trails."
]
for req in non_func_reqs:
    story.append(Paragraph(f"• {req}", styles["Normal"]))

# ---------------------------
# Build PDF
# ---------------------------
doc.build(story)
print(f"PDF generated successfully: {pdf_path}")
