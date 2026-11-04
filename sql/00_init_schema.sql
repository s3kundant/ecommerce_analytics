DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    customer_city VARCHAR(100),
    customer_state CHAR(2),
    first_order_date TIMESTAMP
);

CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
    order_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    items_gmv NUMERIC(10, 2) NOT NULL CHECK (items_gmv >= 0),
    freight_value NUMERIC(10, 2) NOT NULL CHECK (freight_value >= 0)
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL REFERENCES orders(order_id),
    product_id VARCHAR(50) NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    freight_value NUMERIC(10, 2) NOT NULL CHECK (freight_value >= 0)
);

CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at);
CREATE INDEX idx_orders_status_date ON orders(order_status, created_at);