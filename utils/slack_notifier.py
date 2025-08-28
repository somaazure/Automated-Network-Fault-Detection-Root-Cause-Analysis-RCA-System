import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any

class SlackNotifier:
    def __init__(self):
        load_dotenv(override=True)
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        
    def send_notification(self, message: str, incident_data: Dict[str, Any] = None) -> bool:
        """
        Send a notification to Slack channel
        Args:
            message: Main message text
            incident_data: Optional dictionary containing incident details
        Returns:
            bool: True if notification was sent successfully
        """
        if not self.webhook_url:
            print("⚠️ Slack webhook URL not configured")
            return False

        # Basic message block
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *Network Incident Alert*\n{message}"
                }
            }
        ]

        # Add incident details if provided
        if incident_data:
            fields = []
            for key, value in incident_data.items():
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}"
                })

            blocks.append({
                "type": "section",
                "fields": fields
            })

        payload = {
            "blocks": blocks
        }

        try:
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code == 200:
                print("✅ Slack notification sent successfully")
                return True
            else:
                print(f"❌ Failed to send Slack notification: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error sending Slack notification: {str(e)}")
            return False
