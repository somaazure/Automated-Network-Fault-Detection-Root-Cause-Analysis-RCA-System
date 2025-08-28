"""
analytics_engine.py: Parses RCA reports to compute basic metrics/trends for dashboards. 
Utility layer for aggregations used by the Analytics tab.
"""

import os
import re
import pandas as pd
from datetime import datetime

RCA_DIR = os.path.join(os.getcwd(), "rca_reports")

class RCAAnalyticsEngine:
    def __init__(self):
        self.df = pd.DataFrame()

    def parse_reports(self):
        reports = []
        if not os.path.exists(RCA_DIR):
            return pd.DataFrame()

        for file in os.listdir(RCA_DIR):
            if file.endswith(".txt"):
                path = os.path.join(RCA_DIR, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                    # Extract timestamp from filename: rca_2025-08-22_14-20.txt
                    match = re.search(r"(\d{4}-\d{2}-\d{2})", file)
                    timestamp = datetime.strptime(match.group(1), "%Y-%m-%d") if match else None

                    # Extract possible fault category and severity from content
                    category_match = re.search(r"(?:Category|Cause|Issue):\s*(.*)", content, re.IGNORECASE)
                    severity_match = re.search(r"(?:Severity|Impact):\s*(.*)", content, re.IGNORECASE)

                    category = category_match.group(1).strip() if category_match else "Unknown"
                    severity = severity_match.group(1).strip() if severity_match else "Medium"

                    reports.append({
                        "file": file,
                        "timestamp": timestamp,
                        "category": category,
                        "severity": severity,
                        "summary": content[:300]  # preview snippet
                    })

        self.df = pd.DataFrame(reports)
        return self.df

    def get_summary_stats(self):
        if self.df.empty:
            return None

        total_incidents = len(self.df)
        top_categories = self.df["category"].value_counts().head(5)
        severity_counts = self.df["severity"].value_counts()
        incidents_over_time = self.df.groupby("timestamp").size()

        return {
            "total_incidents": total_incidents,
            "top_categories": top_categories,
            "severity_counts": severity_counts,
            "incidents_over_time": incidents_over_time
        }
