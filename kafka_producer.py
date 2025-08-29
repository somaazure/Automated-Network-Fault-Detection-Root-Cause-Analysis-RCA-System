import os
import time
import json
from kafka import KafkaProducer

TOPIC = os.getenv("KAFKA_TOPIC", "network-logs")
BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
LOGS_DIR = os.getenv("LOGS_DIR", os.path.join(os.getcwd(), "logs"))
SLEEP_BETWEEN_LINES = float(os.getenv("SLEEP_BETWEEN_LINES", "0.5"))
LOOP = os.getenv("LOOP", "1") == "1"


def iter_log_lines():
    for fname in sorted(os.listdir(LOGS_DIR)):
        if fname.endswith(".txt"):
            with open(os.path.join(LOGS_DIR, fname), "r", encoding="utf-8") as f:
                for line in f:
                    yield fname, line.rstrip("\n")


def main():
    producer = KafkaProducer(
        bootstrap_servers=[BROKER],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
        linger_ms=50,
    )
    try:
        while True:
            for fname, line in iter_log_lines():
                msg = {"source": fname, "line": line, "ts": time.time()}
                producer.send(TOPIC, key=fname, value=msg)
                time.sleep(SLEEP_BETWEEN_LINES)
            if not LOOP:
                break
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()


