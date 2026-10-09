# Grocery cart datagen for an Estuary PostgreSQL capture

Based on [postgres-simple-capture](https://github.com/estuary/examples/tree/main/postgres-simple-capture).
A local Postgres gets a stream of grocery cart updates, and ngrok exposes it so Estuary can
capture it with CDC.

## What the data looks like

The datagen keeps 3-4 carts open at once. Each `order_id` is assigned a different meal
(see `datagen/meals.py`): Spaghetti Bolognese, Chicken Stir-Fry, Beef Tacos,
Caesar Salad with Salmon, or Pancake Breakfast.

Every 5 seconds it picks one open cart, adds 1-3 items, and **inserts a new row**. Each item
belongs to the order's meal 50% of the time (`ON_MEAL_CHANCE`). Otherwise it's an off-meal
item: an ingredient from another meal, or an everyday staple like coffee or paper towels. When a cart has every
ingredient for its meal, that row has `is_complete = true` and a new `order_id` takes its place.

`public.cart_updates` (append-only):

| column | type | description |
|---|---|---|
| `update_id` | bigserial PK | Global row id |
| `order_id` | text | e.g. `ord-1001`; group rows by this |
| `customer_id` | int | Random customer |
| `update_seq` | int | 1, 2, 3... within the order |
| `added` | jsonb | Only the items added in this update |
| `ingredients` | jsonb | **Full cart at this point**: all earlier items plus `added` |
| `item_count` | int | `jsonb_array_length(ingredients)` |
| `is_complete` | bool | True on the order's last update |
| `updated_at` | timestamptz | Insert time |

Example `ingredients` value:

```json
[{"name": "fresh ginger", "qty": 1, "unit": "piece", "category": "produce"},
 {"name": "sesame oil", "qty": 1, "unit": "bottle", "category": "pantry"},
 {"name": "jasmine rice", "qty": 1, "unit": "2lb bag", "category": "pantry"}]
```

The meal isn't stored in the table, so a downstream app (such as Jev) has to infer it from
the ingredients. The datagen logs show the true meal for each order.

## Setup

1. Copy `.env.example` to `.env` and set `NGROK_AUTHTOKEN`. ngrok TCP tunnels need a
   verified ngrok account (with a card on file).
2. Start the containers: `docker compose up --build -d`
3. Get the Postgres URL:
   `curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'`
   This prints something like `tcp://4.tcp.ngrok.io:12345`.
4. Create a PostgreSQL capture in Estuary:
   - **Address:** the ngrok host and port without `tcp://`, e.g. `4.tcp.ngrok.io:12345`
   - **Database:** `postgres`
   - **User / Password:** `flow_capture` / `password`
   - Select the `public.cart_updates` binding. Its collection key will be `/update_id`,
     so every update stays a separate document.

## Watching it locally

The datagen prints every inserted row, exactly as Postgres stored it, under a header
showing the order, the update number and the true meal:

```bash
docker logs -f jev-datagen
docker exec -it jev-postgres psql -U postgres \
  -c "SELECT order_id, update_seq, item_count, is_complete FROM cart_updates ORDER BY update_id DESC LIMIT 10;"
```

Postgres is also on `localhost:5433` (not 5432, which is often taken by another local
Postgres). Set `POSTGRES_HOST_PORT` to change it.

## Settings

Set these on the `datagen` service in `docker-compose.yml`:

| env var | default | |
|---|---|---|
| `INTERVAL_SECONDS` | `5` | Seconds between rows |
| `ACTIVE_ORDERS` | random 3 or 4 | Open carts at once (at most 4) |
| `ON_MEAL_CHANCE` | `0.5` | Chance each added item belongs to the order's meal (lower = noisier carts) |

## Reset

`docker compose down -v` deletes the database, so the next `up` runs `init.sql` again on an
empty one. After that, recreate the Estuary capture (or backfill it): its replication slot
and position were in the old database. The ngrok address also changes on each restart
unless you have a reserved TCP address, so update the capture's address too.
