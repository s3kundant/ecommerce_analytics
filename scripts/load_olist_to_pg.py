from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ecommerce_analytics")

if DB_PASSWORD:
    db_uri = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    db_uri = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(db_uri)

DATA_DIR = Path("./data")  

auth_str = f"{DB_USER}:{DB_PASSWORD}" if DB_PASSWORD else DB_USER
DATABASE_URL = f"postgresql+psycopg2://{auth_str}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)


def run_etl():
    print(" [1/5] Чтение сырых CSV-файлов Olist...")
    customers_df = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv")
    orders_df = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
    items_df = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    products_df = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")

    
    print(" [2/5] Обработка уникальных пользователей (users)...")
    
    users_clean = customers_df.drop_duplicates(
        subset=["customer_unique_id"]
    ).copy()

    users_to_load = pd.DataFrame()
    users_to_load["external_user_id"] = users_clean["customer_unique_id"]
    users_to_load["email"] = None  
    users_to_load["country_code"] = "BR"  
    users_to_load["city"] = users_clean["customer_city"].str.title()

    np.random.seed(42)
    channels = ["organic", "paid_search", "social_media", "referral", "email"]
    users_to_load["acquisition_channel"] = np.random.choice(
        channels, size=len(users_to_load), p=[0.40, 0.25, 0.20, 0.10, 0.05]
    )

    cust_orders = orders_df.merge(
        customers_df[["customer_id", "customer_unique_id"]],
        on="customer_id",
        how="inner",
    )
    first_order_dates = (
        cust_orders.groupby("customer_unique_id")["order_purchase_timestamp"]
        .min()
        .reset_index()
    )
    users_to_load = users_to_load.merge(
        first_order_dates,
        left_on="external_user_id",
        right_on="customer_unique_id",
        how="left",
    )
    users_to_load["created_at"] = pd.to_datetime(
        users_to_load["order_purchase_timestamp"]
    )
    users_to_load["is_active"] = True
    users_to_load = users_to_load.drop(
        columns=["customer_unique_id", "order_purchase_timestamp"]
    )

    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE TABLE order_items, orders, users RESTART IDENTITY;")
        )

    print(
        f" Загрузка {len(users_to_load)} пользователей в БД..."
    )
    users_to_load.to_sql(
        "users", engine, if_exists="append", index=False, method="multi", chunksize=5000
    )

    db_users = pd.read_sql(
        "SELECT user_id, external_user_id FROM users", engine
    )


    print(" [3/5] Сборка и очистка заказов (orders)...")
    items_df["line_total"] = items_df["price"] + items_df["freight_value"]
    order_totals = (
        items_df.groupby("order_id")["line_total"].sum().reset_index()
    )

    orders_merged = orders_df.merge(
        customers_df[["customer_id", "customer_unique_id"]],
        on="customer_id",
        how="inner",
    )
    orders_merged = orders_merged.merge(
        db_users,
        left_on="customer_unique_id",
        right_on="external_user_id",
        how="inner",
    )
    orders_merged = orders_merged.merge(order_totals, on="order_id", how="left")

    status_map = {
        "delivered": "delivered",
        "shipped": "shipped",
        "canceled": "canceled",
        "unavailable": "canceled",
        "invoiced": "paid",
        "processing": "paid",
        "approved": "paid",
        "created": "created",
    }

    orders_merged["status"] = (
        orders_merged["order_status"].map(status_map).fillna("created")
    )
    orders_merged["total_amount"] = (
        orders_merged["line_total"].fillna(0.00).round(2)
    )
    orders_merged["discount_amount"] = 0.00
    orders_merged["promo_code"] = None
    orders_merged["created_at"] = pd.to_datetime(
        orders_merged["order_purchase_timestamp"]
    )
    orders_merged["paid_at"] = pd.to_datetime(orders_merged["order_approved_at"])
    orders_merged["delivered_at"] = pd.to_datetime(
        orders_merged["order_delivered_customer_date"]
    )


    orders_merged = orders_merged.sort_values("created_at").reset_index(
        drop=True
    )
    orders_merged["db_order_id"] = orders_merged.index + 1

    orders_to_load = orders_merged[
        [
            "user_id",
            "status",
            "total_amount",
            "discount_amount",
            "promo_code",
            "created_at",
            "paid_at",
            "delivered_at",
        ]
    ]

    print(f" Загрузка {len(orders_to_load)} заказов в БД...")
    orders_to_load.to_sql(
        "orders", engine, if_exists="append", index=False, method="multi", chunksize=5000
    )


    order_id_map = orders_merged[["order_id", "db_order_id"]].rename(
        columns={"order_id": "external_order_id", "db_order_id": "order_id"}
    )


    print(" [4/5] Агрегация товарных позиций (order_items)...")
    items_with_cat = items_df.merge(
        products_df[["product_id", "product_category_name"]],
        on="product_id",
        how="left",
    )

    unique_products = items_with_cat["product_id"].unique()
    product_id_map = {
        ext_id: idx + 1 for idx, ext_id in enumerate(unique_products)
    }
    items_with_cat["db_product_id"] = items_with_cat["product_id"].map(
        product_id_map
    )

    items_merged = items_with_cat.merge(
        order_id_map,
        left_on="order_id",
        right_on="external_order_id",
        how="inner",
    )


    items_grouped = (
        items_merged.groupby(["order_id_y", "db_product_id"], as_index=False)
        .agg(
            category_name=("product_category_name", "first"),
            quantity=("order_item_id", "count"),
            unit_price=("price", "mean"),
        )
        .rename(
            columns={"order_id_y": "order_id", "db_product_id": "product_id"}
        )
    )

    items_grouped["category_name"] = items_grouped["category_name"].fillna(
        "uncategorized"
    )
    items_grouped["unit_price"] = items_grouped["unit_price"].round(2)

    print(
        f" Загрузка {len(items_grouped)} позиций чека в БД..."
    )
    items_grouped.to_sql(
        "order_items",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000,
    )

    print(
        " [5/5] ETL успешно завершен! Все данные загружены в PostgreSQL."
    )


if __name__ == "__main__":
    run_etl()