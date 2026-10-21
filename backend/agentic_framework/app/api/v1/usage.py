"""How much of the Groq allowance is used, as percentages."""

import asyncio

from fastapi import APIRouter

from app.core import groq_usage

# Public on purpose (no internal token): it shows percentages only, never a key.
router = APIRouter(prefix="/usage/groq", tags=["Usage"])


@router.get("")
async def groq_usage_percent() -> dict:
    """Percent of the daily allowance used and left: overall, per model, and per key under each model (last 24 hours)."""
    snap = await asyncio.to_thread(groq_usage.snapshot)
    models = {}
    for name, m in snap["models"].items():
        if "percent_used" not in m:
            continue
        keys = {k["name"]: k["models"][name]["percent_used"] for k in snap["keys"] if name in k["models"] and "percent_used" in k["models"][name]}
        models[name] = {"percent_used": m["percent_used"], "percent_left": round(100 - m["percent_used"], 1), "keys": keys}
    used = max((m["percent_used"] for m in models.values()), default=0.0)
    return {"percent_used": used, "percent_left": round(100 - used, 1), "models": models}
