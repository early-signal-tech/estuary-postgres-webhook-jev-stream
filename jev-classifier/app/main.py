"""Receives cart updates from Estuary's webhook materialization and classifies the meal with Jev.

Estuary POSTs a JSON array of collection documents (one per cart_updates row) and retries
on any non-2xx response. The webhook answers right away and classifies in the background,
so a large backfill batch doesn't hold the request open.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from typesafe_sdk import AsyncTypeSafeClient, Choice

log = logging.getLogger("jev_classifier")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Must match the x-webhook-secret custom header in the Estuary materialization.
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
# Number of Jev requests in flight at once.
CONCURRENCY = int(os.environ.get("CONCURRENCY", "4"))
# Skip rows older than this, so the materialization's initial backfill of the whole
# collection doesn't turn into one Jev call per historical row. 0 classifies everything.
MAX_AGE_MINUTES = float(os.environ.get("MAX_AGE_MINUTES", "10"))
# Orders shown on the page.
PAGE_ORDERS = int(os.environ.get("PAGE_ORDERS", "12"))

NO_MEAL = "none"

MEAL_QUESTION = Choice(
    instructions=(
        "A shopper is filling the grocery cart in `cart` one update at a time, so it may be "
        "incomplete and may contain a few unrelated items. Which meal are they most likely "
        "buying ingredients for?"
    ),
    criteria={
        "Spaghetti Bolognese": "Italian pasta with a slow-cooked ground meat and tomato sauce",
        "Chicken Stir-Fry": "Chicken and vegetables stir-fried with Asian sauces, served over rice",
        "Beef Tacos": "Seasoned ground beef in tortillas with cheese, lettuce, tomato and salsa",
        "Caesar Salad with Salmon": "Romaine with Caesar dressing, croutons and parmesan, topped with salmon",
        "Pancake Breakfast": "Homemade pancakes with syrup and fruit, served with a breakfast side",
        NO_MEAL: "The items don't point to any of these meals",
    },
)

orders: dict[str, dict[str, Any]] = {}  # order_id -> latest result plus prediction history
seen_update_ids: set[Any] = set()       # Estuary may resend a batch after a failed request
queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()


def is_too_old(doc: dict[str, Any]) -> bool:
    if not MAX_AGE_MINUTES or not doc.get("updated_at"):
        return False
    try:
        updated_at = datetime.fromisoformat(str(doc["updated_at"]))
    except ValueError:
        return False
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - updated_at > timedelta(minutes=MAX_AGE_MINUTES)


def parse_ingredients(value: Any) -> list[dict[str, Any]]:
    """`ingredients` is a jsonb array, but accept a JSON string too."""
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, list) else []


async def classify(client: AsyncTypeSafeClient, doc: dict[str, Any]) -> None:
    order_id = str(doc.get("order_id"))
    ingredients = parse_ingredients(doc.get("ingredients"))
    seq = doc.get("update_seq") or 0

    try:
        response = await client.system_one(
            state={"cart": ingredients},
            questions={"meal": MEAL_QUESTION},
        )
    except Exception as e:  # keep the worker alive; show the error on the page
        log.error("jev failed for %s #%s: %s", order_id, seq, e)
        order = orders.setdefault(order_id, {"order_id": order_id, "history": []})
        order["error"] = str(e)
        return

    answer = response.choices["meal"]
    probabilities = dict(sorted(answer.probabilities.items(), key=lambda kv: -kv[1]))
    result = {
        "order_id": order_id,
        "customer_id": doc.get("customer_id"),
        "update_id": doc.get("update_id"),
        "update_seq": seq,
        "updated_at": doc.get("updated_at"),
        "is_complete": bool(doc.get("is_complete")),
        "ingredients": ingredients,
        "added": parse_ingredients(doc.get("added")),
        "meal": answer.choice,
        "probability": probabilities.get(answer.choice),
        "confidence": answer.confidence,
        "probabilities": probabilities,
    }

    order = orders.setdefault(order_id, {"order_id": order_id, "history": []})
    order["history"].append({k: result[k] for k in ("update_seq", "meal", "probability")})
    order["history"].sort(key=lambda h: h["update_seq"])
    order.pop("error", None)
    # Results can finish out of order; only a newer update replaces the current one.
    if seq >= order.get("update_seq", 0):
        order.update(result)

    log.info(
        "%s #%s (%d items) -> %s p=%.2f",
        order_id, seq, len(ingredients), answer.choice, result["probability"] or 0,
    )


async def worker(client: AsyncTypeSafeClient) -> None:
    while True:
        doc = await queue.get()
        try:
            await classify(client, doc)
        finally:
            queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncTypeSafeClient(model="jev-latest") as client:  # reads TYPESAFE_API_KEY
        workers = [asyncio.create_task(worker(client)) for _ in range(CONCURRENCY)]
        yield
        for w in workers:
            w.cancel()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook/estuary")
async def webhook(request: Request, x_webhook_secret: str | None = Header(default=None)):
    if WEBHOOK_SECRET and x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="bad secret")

    body = await request.json()
    docs = body if isinstance(body, list) else [body]

    queued = skipped = 0
    for doc in docs:
        if not isinstance(doc, dict) or doc.get("_meta", {}).get("op") == "d":
            continue
        if is_too_old(doc):
            skipped += 1
            continue
        update_id = doc.get("update_id")
        if update_id in seen_update_ids:
            continue
        seen_update_ids.add(update_id)
        queue.put_nowait(doc)
        queued += 1

    log.info(
        "received %d docs, queued %d, skipped %d older than %g min (backlog %d)",
        len(docs), queued, skipped, MAX_AGE_MINUTES, queue.qsize(),
    )
    return {"received": len(docs), "queued": queued, "skipped": skipped}


def order_number(order: dict[str, Any]) -> tuple[int, str]:
    # "ord-9" before "ord-10": compare the trailing number, not the string.
    digits = re.search(r"\d+$", order["order_id"])
    return (int(digits.group()) if digits else -1, order["order_id"])


@app.get("/api/orders")
def api_orders():
    # Pick the most recently updated orders, then show them by order id so cards stay put.
    recent = sorted(
        orders.values(), key=lambda o: str(o.get("updated_at") or ""), reverse=True,
    )[:PAGE_ORDERS]
    return {
        "backlog": queue.qsize(),
        "orders": sorted(recent, key=order_number),
    }


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
