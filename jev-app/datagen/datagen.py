import json
import os
import random
import time

import psycopg2

from meals import MEALS, STAPLES

# Database connection parameters
DB_NAME = os.getenv('POSTGRES_DB', "postgres")
DB_USER = os.getenv('POSTGRES_USER', "postgres")
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', "postgres")
DB_HOST = os.getenv('POSTGRES_HOST', "localhost")
DB_PORT = os.getenv('POSTGRES_PORT', "5432")

INTERVAL_SECONDS = float(os.getenv('INTERVAL_SECONDS', "2"))
# Number of carts being filled at the same time (3 or 4 if not set).
ACTIVE_ORDERS = min(len(MEALS) - 1, int(os.getenv('ACTIVE_ORDERS', random.choice([3, 4]))))
# Chance that each added item belongs to the order's meal. Otherwise it's an off-meal
# item: an ingredient from another meal or an everyday staple.
ON_MEAL_CHANCE = float(os.getenv('ON_MEAL_CHANCE', "0.5"))

INSERT_UPDATE = """
INSERT INTO cart_updates (order_id, customer_id, update_seq, added, ingredients, item_count, is_complete)
VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
RETURNING row_to_json(cart_updates)
"""


class Order:
    def __init__(self, order_id, meal):
        self.order_id = order_id
        self.customer_id = random.randint(1, 1000)
        self.meal = meal
        self.remaining = [dict(item) for item in MEALS[self.meal]]
        random.shuffle(self.remaining)
        self.cart = []
        self.seq = 0

    def next_update(self):
        """Adds 1-3 items, each from the meal with ON_MEAL_CHANCE, and returns what was added."""
        meal_names = {item["name"] for item in MEALS[self.meal]}
        cart_names = {item["name"] for item in self.cart}
        off_meal = [
            item for meal, items in MEALS.items() if meal != self.meal for item in items
        ] + STAPLES
        off_meal = [item for item in off_meal if item["name"] not in meal_names | cart_names]

        added = []
        for _ in range(random.randint(1, 3)):
            if self.remaining and (random.random() < ON_MEAL_CHANCE or not off_meal):
                added.append(self.remaining.pop())
            elif off_meal:
                item = random.choice(off_meal)
                off_meal = [i for i in off_meal if i["name"] != item["name"]]
                added.append(dict(item))

        self.cart.extend(added)
        self.seq += 1
        return added

    @property
    def is_complete(self):
        return not self.remaining


def format_row(row):
    """JSON for the row with one cart item per line."""
    lines = []
    for key, value in row.items():
        if isinstance(value, list):
            items = ",\n".join(f"    {json.dumps(item)}" for item in value)
            lines.append(f'  "{key}": [\n{items}\n  ]' if value else f'  "{key}": []')
        else:
            lines.append(f'  "{key}": {json.dumps(value)}')
    return "{\n" + ",\n".join(lines) + "\n}"


def next_order_number(conn):
    """Continues order numbering from whatever is already in the table."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT max(substring(order_id FROM '[0-9]+$')::int) FROM cart_updates")
        (last,) = cursor.fetchone()
    return (last or 1000) + 1


def connect():
    conn_str = f"dbname='{DB_NAME}' user='{DB_USER}' password='{DB_PASSWORD}' host='{DB_HOST}' port='{DB_PORT}'"
    while True:
        try:
            conn = psycopg2.connect(conn_str)
            next_order_number(conn)  # fails until init.sql has created the table
            return conn
        except psycopg2.Error as e:
            print("Waiting for the database:", str(e).strip())
            time.sleep(2)


def main():
    conn = connect()
    print("Connected to the database!")

    order_number = next_order_number(conn)

    orders = []

    def new_order():
        nonlocal order_number
        # Active orders always get different meals.
        active_meals = {o.meal for o in orders}
        meal = random.choice([m for m in MEALS if m not in active_meals])
        order = Order(f"ord-{order_number}", meal)
        order_number += 1
        print(f"Started {order.order_id} (customer {order.customer_id}): {order.meal}")
        return order

    for _ in range(ACTIVE_ORDERS):
        orders.append(new_order())

    try:
        while True:
            order = random.choice(orders)
            added = order.next_update()

            with conn.cursor() as cursor:
                cursor.execute(INSERT_UPDATE, (
                    order.order_id,
                    order.customer_id,
                    order.seq,
                    json.dumps(added),
                    json.dumps(order.cart),
                    len(order.cart),
                    order.is_complete,
                ))
                (row,) = cursor.fetchone()
            conn.commit()

            # Print the row exactly as stored in Postgres (what Estuary captures).
            print(f"\n=== {order.order_id} update #{order.seq} ({order.meal}) "
                  f"+{len(added)} -> {len(order.cart)} items ===")
            print(format_row(row))

            if order.is_complete:
                print(f"Completed {order.order_id}: {order.meal}")
                orders.remove(order)
                orders.append(new_order())

            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Process interrupted by user.")
    finally:
        conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()
