# Cart meal scorer

Streams grocery cart updates through Estuary and has Jev (TypeSafe) guess which meal
each cart is being built for, live.

```
jev-app datagen → Postgres cart_updates → Estuary Postgres capture → collection
   → Estuary HTTP Webhook materialization → ngrok → jev-classifier (FastAPI) → Jev → web page
```

| folder | what it is |
|---|---|
| [`jev-app/`](jev-app) | Postgres + a datagen that inserts grocery cart updates, exposed to Estuary over an ngrok TCP tunnel for CDC capture |
| [`jev-classifier/`](jev-classifier) | FastAPI app that receives the rows from an Estuary webhook materialization, classifies each cart with Jev, and shows the results on a web page |

## Quick start

1. **Set your keys once.** In this folder, copy `.env.example` to `.env` and set
   `NGROK_AUTHTOKEN`, `TYPESAFE_API_KEY` and `WEBHOOK_SECRET`. Both apps read it.
2. **Start both apps.** Run `docker compose up --build -d` in `jev-app/` and then in
   `jev-classifier/`.
3. **Set up Estuary.** Create a Postgres capture (which creates the `cart_updates`
   collection) and an HTTP Webhook materialization that sends it to the classifier. Follow
   [Setting up Estuary](#setting-up-estuary), using the UI, flowctl, or an agent.
4. **Watch it.** Open http://localhost:8000. `docker logs -f jev-datagen` shows the true
   meal for each order, so you can compare it with Jev's guess.

## Getting the ngrok addresses

Each app runs its own ngrok tunnel, and Estuary needs both public addresses. The commands
below use `jq`. Without it, open the ngrok inspector in a browser and copy the URL shown
there instead.

### jev-app: Postgres address for the Estuary capture

```bash
curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'
# tcp://4.tcp.ngrok.io:12345
```

In the capture's **Address** field, enter the host and port without `tcp://`, e.g.
`4.tcp.ngrok.io:12345`. Inspector: http://localhost:4040.

### jev-classifier: webhook address for the Estuary materialization

```bash
curl -s http://localhost:4041/api/tunnels | jq -r '.tunnels[0].public_url'
# https://abc123.ngrok-free.app
```

In the materialization's **Address** field, enter that URL with a trailing `/`, e.g.
`https://abc123.ngrok-free.app/`. Set **Relative path** to `webhook/estuary`, and add an
`x-webhook-secret` header set to your `WEBHOOK_SECRET`. Inspector: http://localhost:4041.

Both addresses change whenever their ngrok container restarts, unless you have a reserved
ngrok domain or TCP address. When they change, update the Estuary capture or
materialization.

## Setting up Estuary

You need two things in Estuary:

1. **A PostgreSQL capture** from jev-app's database. It creates the `cart_updates`
   collection, with one document per row, keyed on `/update_id`.
2. **An HTTP Webhook materialization** that reads that collection and POSTs each document
   to jev-classifier through its ngrok tunnel.

Start both apps first (Quick start, step 2) so the ngrok addresses exist. Then pick one of
the three options below.

| setting | value |
|---|---|
| Postgres address | [jev-app ngrok address](#jev-app-postgres-address-for-the-estuary-capture) without `tcp://`, e.g. `4.tcp.ngrok.io:12345` |
| Database / user / password | `postgres` / `flow_capture` / `password` (created by `jev-app/postgres/init.sql`) |
| Table | `public.cart_updates` (already in the `flow_publication` publication) |
| Webhook address | [jev-classifier ngrok URL](#jev-classifier-webhook-address-for-the-estuary-materialization) with a trailing `/`, e.g. `https://abc123.ngrok-free.app/` |
| Webhook relative path | `webhook/estuary` |
| Webhook header | `x-webhook-secret` = your `WEBHOOK_SECRET` from `.env` |

### Option A: Estuary UI

**Capture (creates the collection)**

1. In the [Estuary dashboard](https://dashboard.estuary.dev), go to **Sources** →
   **New Capture** and choose **PostgreSQL**.
2. Name it, e.g. `jev-app`. Fill in **Server Address**, **Database**, **User** and
   **Password** from the table above. Leave **History Mode** off.
3. Click **Next**. Estuary connects and discovers the tables. Keep only the
   `public.cart_updates` binding (turn off `flow_watermarks` if it's listed).
4. Click **Save and Publish**. The capture backfills, then shows **Streaming CDC Events**.
   You can see the new `cart_updates` collection under **Collections**, and click it to
   watch documents arrive.

**Webhook materialization**

1. Go to **Destinations** → **New Materialization** and choose **HTTP Webhook**.
2. Name it, e.g. `jev-classifier`. Set **Address** to the webhook address. Under
   **Headers**, add a custom header named `x-webhook-secret` whose value is your
   `WEBHOOK_SECRET`.
3. Under **Source Collections**, add the `cart_updates` collection, and set its
   **Relative Path** to `webhook/estuary`.
4. Click **Next**, then **Save and Publish**.

### Option B: flowctl CLI

Install [flowctl](https://docs.estuary.dev/guides/get-started-with-flowctl/) and run
`flowctl auth login`. Both specs are templates in this repo. Replace `YOUR_PREFIX` with your
Estuary prefix (shown in the dashboard, e.g. `acmeCo/`) and fill in the addresses.

Both templates hold values you shouldn't commit (your prefix, ngrok addresses, the
webhook secret), and `flowctl discover` rewrites its file in place. So work on copies in a
`local/` folder, which `.gitignore` excludes.

**Capture:** copy the template and set `address` in the copy:

```bash
cd jev-app
mkdir -p local && cp capture.flow.yaml local/ && cd local
flowctl discover --source capture.flow.yaml --flat   # adds the cart_updates binding + collection spec
# Review the bindings; remove flow_watermarks if discover added it.
flowctl catalog publish --source capture.flow.yaml
flowctl catalog status YOUR_PREFIX/jev-app           # expect: Streaming CDC Events
```

The collection is named `YOUR_PREFIX/jev-app/cart_updates`. To check, run
`flowctl catalog list --collections --prefix YOUR_PREFIX/`.

**Materialization:** copy the template and set `address`, the `x-webhook-secret` value and
`source` in the copy:

```bash
cd ../../jev-classifier
mkdir -p local && cp materialize.flow.yaml local/ && cd local
flowctl catalog publish --source materialize.flow.yaml
flowctl catalog status YOUR_PREFIX/jev-classifier
```

When an ngrok address changes, edit the copy in `local/` and run `publish` again.

### Option C: an agent

A coding agent that can run `flowctl` (for example Claude Code, with Estuary's agent
skills installed) can do Option B for you. Run `flowctl auth login` yourself first, start
both apps, and then give it something like:

> Using flowctl, create a PostgreSQL CDC capture named `YOUR_PREFIX/jev-app` from
> `jev-app/capture.flow.yaml`. The Postgres address is the jev-app ngrok TCP tunnel (get
> it from `http://localhost:4040/api/tunnels`). Capture only `public.cart_updates`.
> Discover, publish, and confirm it reaches Streaming CDC Events.

> Using flowctl, create an HTTP Webhook materialization named `YOUR_PREFIX/jev-classifier`
> from `jev-classifier/materialize.flow.yaml`. Its source is the `cart_updates` collection
> created by the jev-app capture. The address is the jev-classifier ngrok URL (from
> `http://localhost:4041/api/tunnels`) with a trailing `/`. The relative path is
> `webhook/estuary`, and the `x-webhook-secret` header comes from `WEBHOOK_SECRET` in
> `.env`. Publish it and confirm that `docker logs jev-classifier` shows classifications.

Review the specs it writes before it publishes, especially the secret header.

### Checking that it works

- `docker logs -f jev-classifier` prints one line per classified update.
- http://localhost:4041 (the classifier's ngrok inspector) shows each POST from Estuary.
  A `401` means the `x-webhook-secret` header doesn't match `WEBHOOK_SECRET`.
- The classifier skips rows older than `MAX_AGE_MINUTES` (default 10). So when the capture
  first backfills old rows, only recent ones show up on the page.

## Requirements

- Docker
- An [Estuary](https://estuary.dev) account
- An [ngrok](https://ngrok.com) account (TCP tunnels need a verified account)
- A [TypeSafe](https://console.typesafe.ai/) API key

## Secrets

Both apps read their keys from the single `.env` in this folder (via `env_file: ../.env`
in each `docker-compose.yml`), which `.gitignore` keeps out of the repo. Only
`.env.example` is committed.
