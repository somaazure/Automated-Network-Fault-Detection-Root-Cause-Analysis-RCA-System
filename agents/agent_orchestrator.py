"""
Orchestrates the end-to-end incident flow using Semantic Kernel 
(severity classification → RCA generation → Slack notify → save RCA file). 
Manages Azure OpenAI client setup, prompt formatting, function registration, and invokes agents.
"""

import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.functions import KernelArguments
from agents.prompts import (
    INCIDENT_MANAGER, INCIDENT_MANAGER_INSTRUCTIONS,
    NETWORK_OPS_ASSISTANT, NETWORK_OPS_ASSISTANT_INSTRUCTIONS,
    SEVERITY_CLASSIFIER, SEVERITY_CLASSIFIER_INSTRUCTIONS,
    ROOT_CAUSE_ANALYSIS, ROOT_CAUSE_ANALYSIS_INSTRUCTIONS
)
from utils.slack_notifier import SlackNotifier
from dotenv import load_dotenv

class AgentOrchestrator:
    def __init__(self):
        load_dotenv(override=True)
        self.kernel = sk.Kernel()
        self.slack = SlackNotifier()
        # Configure Azure OpenAI
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION") or "2024-07-01-preview"
        if not azure_endpoint or not azure_api_key or not azure_deployment:
            raise RuntimeError(
                "Missing Azure OpenAI configuration. Please set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT_NAME in your environment or .env file."
            )
        try:
            self.kernel.add_service(
                AzureChatCompletion(
                    deployment_name=azure_deployment,
                    endpoint=azure_endpoint,
                    api_key=azure_api_key,
                    api_version=azure_api_version
                )
            )
        except Exception as ex:
            raise RuntimeError(
                f"Failed to initialize Azure OpenAI client: {ex}. Verify endpoint (https://<resource>.openai.azure.com), deployment name, API key, and API version ({azure_api_version})."
            )
        
        # Initialize agents (only those with instructions)
        if SEVERITY_CLASSIFIER_INSTRUCTIONS.strip():
            self.create_agent(SEVERITY_CLASSIFIER, SEVERITY_CLASSIFIER_INSTRUCTIONS)
        
        if ROOT_CAUSE_ANALYSIS_INSTRUCTIONS.strip():
            self.create_agent(ROOT_CAUSE_ANALYSIS, ROOT_CAUSE_ANALYSIS_INSTRUCTIONS)

    def create_agent(self, name, instructions):
        execution_settings = PromptExecutionSettings(max_tokens=2000, temperature=0.7)
        return self.kernel.add_function(
            plugin_name="network_agents",
            function_name=name,
            prompt=instructions,
            prompt_execution_settings=execution_settings
        )

    def read_log_file(self, log_file_path):
        """Read and return the content of a log file"""
        try:
            with open(log_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return content
        except Exception as e:
            return f"Error reading log file: {str(e)}"

    def save_rca_report(self, log_file_path, rca_content):
        """Save RCA report to rca_reports folder"""
        try:
            # Create rca_reports directory if it doesn't exist
            rca_dir = os.path.join(os.getcwd(), "rca_reports")
            os.makedirs(rca_dir, exist_ok=True)
            
            # Generate filename based on log file
            log_filename = os.path.basename(log_file_path)
            rca_filename = f"rca_{os.path.splitext(log_filename)[0]}.txt"
            rca_filepath = os.path.join(rca_dir, rca_filename)
            
            # Clean up the RCA content
            cleaned_content = str(rca_content)
            
            # Extract markdown content between ```markdown and ```
            if "```markdown" in cleaned_content:
                start = cleaned_content.find("```markdown")
                end = cleaned_content.find("```", start + 3)
                if end != -1:
                    cleaned_content = cleaned_content[start + 3:end].strip()
            
            # If still contains Python code, clean it further
            if "def " in cleaned_content or "rca_markdown =" in cleaned_content:
                lines = cleaned_content.split('\n')
                content_lines = []
                in_content = False
                
                for line in lines:
                    # Skip Python function definitions and variable assignments
                    if any(skip in line.strip() for skip in ['def ', 'rca_markdown =', 'logfile =', 'save_rca_report']):
                        continue
                    # Skip empty lines at the beginning
                    if not in_content and not line.strip():
                        continue
                    # Start capturing after the first non-empty, non-Python line
                    if not in_content and line.strip() and not line.strip().startswith('#'):
                        in_content = True
                    if in_content:
                        content_lines.append(line)
                
                if content_lines:
                    cleaned_content = '\n'.join(content_lines).strip()
            
            # Write the cleaned content to file
            with open(rca_filepath, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            print(f"✅ RCA report saved: {rca_filepath}")
            return rca_filepath
            
        except Exception as e:
            print(f"❌ Error saving RCA report: {str(e)}")
            return None

    async def process_network_incident(self, log_file_path):
        # Read the actual log content
        log_content = self.read_log_file(log_file_path)
        
        # Format the prompts with log content
        severity_prompt = SEVERITY_CLASSIFIER_INSTRUCTIONS.format(log_content=log_content)
        rca_prompt = ROOT_CAUSE_ANALYSIS_INSTRUCTIONS.format(
            log_content=log_content,
            severity_classification="To be determined"
        )
        
        # Create agents with formatted prompts
        severity_agent = self.kernel.add_function(
            plugin_name="network_agents",
            function_name=SEVERITY_CLASSIFIER,
            prompt=severity_prompt,
            prompt_execution_settings=PromptExecutionSettings(max_tokens=2000, temperature=0.7)
        )
        
        # 1. Severity Classification
        severity_response = await self.kernel.invoke(
            plugin_name="network_agents",
            function_name=SEVERITY_CLASSIFIER,
            arguments=KernelArguments()
        )

        # Send severity notification
        self.slack.send_notification(
            "Network incident severity classified",
            {
                "Log File": os.path.basename(log_file_path),
                "Severity": str(severity_response)
            }
        )

        # Update RCA prompt with actual severity classification
        rca_prompt = ROOT_CAUSE_ANALYSIS_INSTRUCTIONS.format(
            log_content=log_content,
            severity_classification=str(severity_response)
        )
        
        # Create RCA agent with updated prompt
        rca_agent = self.kernel.add_function(
            plugin_name="network_agents",
            function_name=ROOT_CAUSE_ANALYSIS,
            prompt=rca_prompt,
            prompt_execution_settings=PromptExecutionSettings(max_tokens=2000, temperature=0.7)
        )

        # 2. RCA Agent generates analysis report
        rca_response = await self.kernel.invoke(
            plugin_name="network_agents",
            function_name=ROOT_CAUSE_ANALYSIS,
            arguments=KernelArguments()
        )

        # Send RCA notification
        self.slack.send_notification(
            "Root Cause Analysis completed",
            {
                "RCA Summary": str(rca_response)[:500] + "..."  # Truncate for Slack
            }
        )

        # Save RCA report to file
        rca_filepath = self.save_rca_report(log_file_path, rca_response)

        return {
            "severity_response": str(severity_response),
            "rca_response": str(rca_response)
        }
