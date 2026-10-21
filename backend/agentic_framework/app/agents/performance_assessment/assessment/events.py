"""Run events: what the live pipeline view and the logs show.

Every graph node runs inside ``events.node(path)``: it records ``node_start``, any ``log`` / ``tool`` / ``llm`` events the node reports, and ``node_end`` (with the duration) or ``node_error``.
The path says where the node is: ``team/prepare_workspace`` or ``student:STU-014/factor_effort``. The frontend draws the pipeline from the topology (shared/performance/topology.py) and lights up nodes by these events.

Events go to a store with ``add_events`` (the PostgreSQL ``PerformanceStore`` in production, ``MemoryStore`` in tests). Nothing secret is ever put in an event: callers pass summaries (counts, names,
short reasons), never tokens, raw repository text or student answers.

Writing is off the run's path: ``emit`` puts the event on a queue and returns at once; one background thread per run writes the queue in order, several events per round trip. The database can be
far away (about a second per statement), and a run that waited for each event spent more time logging than assessing. ``flush`` waits until everything queued has been written; the runner calls it
when a run ends or stops to wait for a person. If the database refuses a write, the batch is tried once more and then dropped with a log line: a progress marker must never stop a run.
"""
import logging
import queue
import threading
import time
from contextlib import asynccontextmanager

log = logging.getLogger(__name__)
_writers: dict = {}
_registry_lock = threading.Lock()
BATCH = 100


class _Writer:
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id
        self.q: queue.Queue = queue.Queue()
        self.thread = threading.Thread(target=self._loop, name=f"events-{str(run_id)[:8]}", daemon=True)
        self.thread.start()

    def put(self, item):
        self.q.put(item)

    def flush(self, timeout=60.0):
        done = threading.Event()
        self.q.put(("flush", done))
        return done.wait(timeout)

    def _loop(self):
        while True:
            items = [self.q.get()]
            try:
                while len(items) < BATCH:
                    items.append(self.q.get_nowait())
            except queue.Empty:
                pass
            events = [i[1] for i in items if i[0] == "event"]
            node = next((i[1] for i in reversed(items) if i[0] == "node"), None)
            for attempt in (1, 2):
                try:
                    if events:
                        self.store.add_events(self.run_id, events)
                    if node:
                        self.store.update_run(self.run_id, current_node=node)
                    break
                except Exception as e:  # the database may be busy or refuse a connection; one more try, then drop
                    if attempt == 2:
                        log.warning("run %s: %d events could not be written (%s: %s)", self.run_id, len(events), type(e).__name__, str(e)[:120])
                    else:
                        time.sleep(1.0)
            stop = False
            for i in items:
                if i[0] == "flush":
                    i[1].set()
                stop = stop or i[0] == "stop"
                self.q.task_done()
            if stop:
                return


def _writer(store, run_id) -> _Writer:
    key = (id(store), str(run_id))
    with _registry_lock:
        if key not in _writers:
            _writers[key] = _Writer(store, run_id)
        return _writers[key]


def close(store, run_id, timeout=60.0) -> None:
    """Write what is queued and end the run's writer thread (a later event for the same run starts a new one)."""
    key = (id(store), str(run_id))
    with _registry_lock:
        w = _writers.pop(key, None)
    if w is not None:
        w.flush(timeout)
        w.put(("stop", None))


def flush(store, run_id, timeout=60.0) -> bool:
    """Wait until every event queued for this run has been written. True when it was done in time."""
    key = (id(store), str(run_id))
    with _registry_lock:
        w = _writers.get(key)
    return True if w is None else w.flush(timeout)


class NodeLog:
    def __init__(self, events, path):
        self.events, self.path = events, path

    def log(self, message, level="info", **payload):
        self.events.emit("log", message, node_path=self.path, level=level, payload=payload)

    def tool(self, name, summary="", **payload):
        p = {"tool": name}
        if summary:
            p["summary"] = summary
            if "output" not in payload and "output_preview" not in payload:
                p["output"] = summary
        p.update(payload)
        self.events.emit("tool", f"{name}: {summary}" if summary else name, node_path=self.path, payload=p)

    def llm(self, summary, **payload):
        self.events.emit("llm", summary, node_path=self.path, payload=payload)

    def thinking(self, summary="", thinking="", duration=None, tokens=None, **payload):
        self.events.emit("thinking", summary or "Agent Reasoning", node_path=self.path,
                         payload={"thinking": thinking, "duration": duration, "tokens": tokens, **payload})

    def decision(self, summary="", **payload):
        self.events.emit("decision", summary or "Agent Decision", node_path=self.path, payload=payload)

    def produce(self, field, *, verified=False, fallback=False, message=""):
        self.events.emit("produce", message or field, node_path=self.path,
                         payload={"field": field, "verified": bool(verified), "fallback": bool(fallback)})

    def result(self, **payload):
        self.payload = payload
        self.events.emit("result", "", node_path=self.path, payload=payload)

    def task(self, event, task, **payload):
        """Record typed Requirement Fulfillment progress without encoding it in log text."""
        self.events.emit("task", "", node_path=self.path,
                         payload={"event": event, "task": task, **payload})


class Events:
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id
        self._w = _writer(store, run_id)

    def emit(self, type, message="", *, node_path="", level="info", payload=None):
        self._w.put(("event", {"type": type, "message": message, "node_path": node_path, "level": level, "payload": payload or {}}))

    def llm(self, node_path, summary, **payload):
        self.emit("llm", summary, node_path=node_path, payload=payload)

    def thinking(self, node_path, summary="", thinking="", duration=None, tokens=None, **payload):
        self.emit("thinking", summary or "Agent Reasoning", node_path=node_path,
                  payload={"thinking": thinking, "duration": duration, "tokens": tokens, **payload})

    def decision(self, node_path, summary="", **payload):
        self.emit("decision", summary or "Agent Decision", node_path=node_path, payload=payload)

    def task(self, node_path, event, task, **payload):
        self.emit("task", "", node_path=node_path,
                  payload={"event": event, "task": task, **payload})

    def flush(self, timeout=60.0):
        return self._w.flush(timeout)

    @asynccontextmanager
    async def node(self, path):
        t0 = time.time()
        self.emit("node_start", path.split("/")[-1], node_path=path)
        self._w.put(("node", path))
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
        self.emit("node_end", path.split("/")[-1], node_path=path, payload={"seconds": round(time.time() - t0, 2), "result": n.payload, **n.payload})
