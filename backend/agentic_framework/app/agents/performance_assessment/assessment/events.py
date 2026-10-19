"""Run events: what the live pipeline view and the logs show.

Every graph node runs inside ``events.node(path)``: it records ``node_start``, any ``log`` / ``tool`` / ``llm`` events the node reports, and ``node_end`` (with the duration) or ``node_error``.
The path says where the node is: ``team/prepare_workspace`` or ``student:STU-014/factor_effort``. The frontend draws the pipeline from ``TOPOLOGY`` (graph.py) and lights up nodes by these events.

Events go to a store with ``add_event`` (the PostgreSQL ``PerformanceStore`` in production, ``MemoryStore`` in tests). Nothing secret is ever put in an event: callers pass summaries (counts, names,
short reasons), never tokens, raw repository text or student answers.
"""
import time
from contextlib import asynccontextmanager


class NodeLog:
    def __init__(self, events, path):
        self.events, self.path = events, path

    def log(self, message, level="info", **payload):
        self.events.emit("log", message, node_path=self.path, level=level, payload=payload)

    def tool(self, name, summary="", **payload):
        self.events.emit("tool", f"{name}: {summary}" if summary else name, node_path=self.path, payload={"tool": name, **payload})

    def llm(self, summary, **payload):
        self.events.emit("llm", summary, node_path=self.path, payload=payload)

    def result(self, **payload):
        self.payload = payload


class Events:
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id

    def emit(self, type, message="", *, node_path="", level="info", payload=None):
        return self.store.add_event(self.run_id, type, message, node_path=node_path, level=level, payload=payload or {})

    @asynccontextmanager
    async def node(self, path):
        t0 = time.time()
        self.emit("node_start", path.split("/")[-1], node_path=path)
        try:
            self.store.update_run(self.run_id, current_node=path)
        except Exception:  # a progress marker must never stop a run
            pass
        n = NodeLog(self, path)
        n.payload = {}
        try:
            yield n
        except BaseException as e:
            if type(e).__name__ == "GraphInterrupt":  # waiting for a human is not an error
                self.emit("node_wait", "waiting for a decision", node_path=path, level="warn", payload={"seconds": round(time.time() - t0, 2)})
                raise
            self.emit("node_error", f"{type(e).__name__}: {str(e)[:300]}", node_path=path, level="error", payload={"seconds": round(time.time() - t0, 2)})
            raise
        self.emit("node_end", path.split("/")[-1], node_path=path, payload={"seconds": round(time.time() - t0, 2), **n.payload})
