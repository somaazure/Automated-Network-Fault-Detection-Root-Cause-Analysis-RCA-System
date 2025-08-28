"""
log_processor.py: Scans logs/, generates RCA summaries using OpenAI, and writes them into rca_reports/. 
Simple batch processor independent of the agent pipeline.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

class LogProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def process_logs(self, logs_dir, rca_dir):
        """
        Processes log files into RCA summaries and saves them in rca_reports.
        """
        if not os.path.exists(logs_dir):
            return 0

        os.makedirs(rca_dir, exist_ok=True)
        reports_generated = 0

        for file in os.listdir(logs_dir):
            if file.endswith((".log", ".txt")):
                log_path = os.path.join(logs_dir, file)
                report_path = os.path.join(rca_dir, f"rca_{os.path.splitext(file)[0]}.txt")

                # Skip already processed logs
                if os.path.exists(report_path):
                    continue

                with open(log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()

                # Generate RCA using OpenAI
                prompt = f"""
                You are a network RCA assistant. Analyze these logs and summarize:
                1. Root cause
                2. Severity level
                3. Impacted components
                4. Resolution steps

                Logs:
                {log_content[:4000]}
                """
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    rca_summary = response.choices[0].message.content
                except Exception as e:
                    print(f"❌ Error processing {file}: {e}")
                    continue

                with open(report_path, "w", encoding="utf-8") as rf:
                    rf.write(rca_summary)

                reports_generated += 1

        return reports_generated
