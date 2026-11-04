DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    user_id VARCHAR(64) PRIMARY KEY,
    first_order_date TIMESTAMP,
    customer_city VARCHAR(128),
    customer_state VARCHAR(8)
);

CREATE TABLE orders (
    order_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id),
    order_status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    delivered_at TIMESTAMP,
    items_gmv NUMERIC(12, 2) NOT NULL DEFAULT 0,
    freight_value NUMERIC(12, 2) NOT NULL DEFAULT 0
);

CREATE TABLE order_items (
    order_id VARCHAR(64) NOT NULL REFERENCES orders(order_id),
    order_item_id INT NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    seller_id VARCHAR(64) NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    freight_value NUMERIC(12, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE INDEX idx_orders_user_created ON orders(user_id, created_at);
CREATE INDEX idx_orders_status_date ON orders(order_status, created_at);
CREATE INDEX idx_orders_created_at ON orders(created_at);