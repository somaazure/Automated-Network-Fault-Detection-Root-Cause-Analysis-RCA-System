import os
import json
import time
import asyncio
from collections import defaultdict
from kafka import KafkaConsumer
from dotenv import load_dotenv

from agents.agent_orchestrator import AgentOrchestrator

TOPIC = os.getenv("KAFKA_TOPIC", "network-logs")
BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
OUT_DIR = os.getenv("STREAM_LOG_DIR", os.path.join(os.getcwd(), "logs", "ingested"))
DEBOUNCE_SEC = float(os.getenv("DEBOUNCE_SEC", "5"))

last_seen = defaultdict(float)
pending_tasks = {}


def append_line(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def process_file(orch: AgentOrchestrator, path: str) -> None:
    try:
        res = await orch.process_network_incident(path)
        print(f"[Processed] {os.path.basename(path)} | Severity: {res['severity_response']}")
    except Exception as e:
        print(f"[Error] {path}: {e}")


async def debounce_loop(orch: AgentOrchestrator) -> None:
    while True:
        now = time.time()
        for filepath, ts in list(last_seen.items()):
            if now - ts >= DEBOUNCE_SEC and filepath not in pending_tasks:
                pending_tasks[filepath] = asyncio.create_task(process_file(orch, filepath))
        # cleanup finished tasks
        for fp, t in list(pending_tasks.items()):
            if t.done():
                pending_tasks.pop(fp, None)
        await asyncio.sleep(1)


async def main() -> None:
    load_dotenv(override=True)
    orch = AgentOrchestrator()
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=[BROKER],
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    asyncio.create_task(debounce_loop(orch))
    for msg in consumer:
        source = msg.key or "unknown.log"
        data = msg.value
        line = data.get("line", "")
        out_path = os.path.join(OUT_DIR, f"stream_{source}")
        append_line(out_path, line)
        last_seen[out_path] = time.time()


if __name__ == "__main__":
    asyncio.run(main())


