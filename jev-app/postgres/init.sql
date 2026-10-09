-- Step 1: Create the flow_capture user with replication role
CREATE USER flow_capture WITH REPLICATION PASSWORD 'password';

-- Step 2: Grant read access and necessary privileges to flow_capture
GRANT pg_read_all_data TO flow_capture;
GRANT pg_write_all_data TO flow_capture;

-- Step 3: Create the flow_watermarks table and assign privileges
CREATE TABLE IF NOT EXISTS public.flow_watermarks (
    slot TEXT PRIMARY KEY,
    watermark TEXT
);

-- Grant privileges to flow_capture for the flow_watermarks table
GRANT ALL PRIVILEGES ON TABLE public.flow_watermarks TO flow_capture;

-- Step 4: Create the publication and add tables
CREATE PUBLICATION flow_publication;
ALTER PUBLICATION flow_publication SET (publish_via_partition_root = true);

-- Add flow_watermarks table to the publication
ALTER PUBLICATION flow_publication ADD TABLE public.flow_watermarks;

-- Step 5: Create the cart_updates table.
-- Append-only: every change to a cart is a new row. `ingredients` holds the
-- full cart at that point in time; `added` holds only what this update added.
CREATE TABLE IF NOT EXISTS public.cart_updates (
    update_id   BIGSERIAL PRIMARY KEY,
    order_id    TEXT        NOT NULL,
    customer_id INTEGER     NOT NULL,
    update_seq  INTEGER     NOT NULL,
    added       JSONB       NOT NULL,
    ingredients JSONB       NOT NULL,
    item_count  INTEGER     NOT NULL,
    is_complete BOOLEAN     NOT NULL DEFAULT FALSE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (order_id, update_seq)
);

CREATE INDEX IF NOT EXISTS cart_updates_order_id_idx ON public.cart_updates (order_id);

-- Add the cart_updates table to the publication
ALTER PUBLICATION flow_publication ADD TABLE public.cart_updates;
