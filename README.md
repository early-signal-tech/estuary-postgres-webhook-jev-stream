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

1. **Start the data source.** In `jev-app/`, copy `.env.example` to `.env`, set
   `NGROK_AUTHTOKEN`, run `docker compose up --build -d`, and create a PostgreSQL
   capture in Estuary for `public.cart_updates`. See [`jev-app/README.md`](jev-app/README.md).
2. **Start the classifier.** In `jev-classifier/`, copy `.env.example` to `.env`, set
   `TYPESAFE_API_KEY`, `WEBHOOK_SECRET` and `NGROK_AUTHTOKEN`, run
   `docker compose up --build -d`, and create an HTTP Webhook materialization from the
   `cart_updates` collection. See [`jev-classifier/README.md`](jev-classifier/README.md).
3. **Watch it.** Open http://localhost:8000. `docker logs -f jev-datagen` shows the true
   meal for each order, so you can compare it with Jev's guess.

## Requirements

- Docker
- An [Estuary](https://estuary.dev) account
- An [ngrok](https://ngrok.com) account (TCP tunnels need a verified account)
- A [TypeSafe](https://console.typesafe.ai/) API key

## Secrets

Each app reads its keys from its own `.env`, which `.gitignore` keeps out of the repo.
Only the `.env.example` files are committed.
