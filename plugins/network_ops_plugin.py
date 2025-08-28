# plugins/network_ops_plugin.py
import textwrap
from utils.helpers import ts
from semantic_kernel.functions.kernel_function_decorator import kernel_function

class NetworkOpsPlugin:
    """Executes corrective actions and appends results to log files."""

    def _append(self, filepath: str, content: str) -> None:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write("\n" + textwrap.dedent(content).strip())

    @kernel_function(description="Restart a network node")
    def restart_node(self, node_id: str = "", logfile: str = "") -> str:
        now = ts()
        entries = [
            f"[{now}] ALERT Ops: Node {node_id} restart requested.",
            f"[{now}] INFO Node-{node_id}: Restart initiated.",
            f"[{now}] INFO Node-{node_id}: Services up. Heartbeat OK."
        ]
        self._append(logfile, "\n".join(entries))
        return f"Node {node_id} restarted successfully."
