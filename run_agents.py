import asyncio
import os
from agents.agent_orchestrator import AgentOrchestrator
from dotenv import load_dotenv

async def main():
    load_dotenv(override=True)
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator()
    
    # Process logs directory
    logs_dir = os.path.join(os.getcwd(), "logs")
    for log_file in os.listdir(logs_dir):
        if log_file.endswith(".txt"):
            log_path = os.path.join(logs_dir, log_file)
            print(f"Processing {log_file}...")
            
            # Process the incident
            results = await orchestrator.process_network_incident(log_path)
            
            # Print results
            print("Severity Classification:", results["severity_response"])
            print("RCA Response:", results["rca_response"])
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
