import os
import csv
from io import StringIO
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ecommerce_analytics")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SQL_DIR = os.path.join(BASE_DIR, "sql")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def get_engine():
    auth = f"{DB_USER}:{DB_PASSWORD}" if DB_PASSWORD else DB_USER
    db_url = f"postgresql+psycopg2://{auth}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(db_url)


def psql_insert_copy(table, conn, keys, data_iter):
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)
        columns = ", ".join(f'"{k}"' for k in keys)
        table_name = f"{table.schema}.{table.name}" if table.schema else table.name
        sql = f"COPY {table_name} ({columns}) FROM STDIN WITH CSV"
        cur.copy_expert(sql=sql, file=s_buf)


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    engine = get_engine()

    customers = pd.read_csv(os.path.join(DATA_DIR, "olist_customers_dataset.csv"))
    orders = pd.read_csv(os.path.join(DATA_DIR, "olist_orders_dataset.csv"))
    items = pd.read_csv(os.path.join(DATA_DIR, "olist_order_items_dataset.csv"))

    orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"])
    orders["order_delivered_customer_date"] = pd.to_datetime(orders["order_delivered_customer_date"])

    orders_with_users = orders.merge(
        customers[["customer_id", "customer_unique_id", "customer_city", "customer_state"]],
        on="customer_id",
        how="inner",
    )

    delivered_dates = (
        orders_with_users[orders_with_users["order_status"] == "delivered"]
        .groupby("customer_unique_id")["order_purchase_timestamp"]
        .min()
        .reset_index()
        .rename(columns={"order_purchase_timestamp": "first_order_date"})
    )

    users_meta = (
        orders_with_users.sort_values("order_purchase_timestamp")
        .groupby("customer_unique_id")
        .agg(
            customer_city=("customer_city", "first"),
            customer_state=("customer_state", "first"),
        )
        .reset_index()
    )

    users_df = users_meta.merge(delivered_dates, on="customer_unique_id", how="left").rename(
        columns={"customer_unique_id": "user_id"}
    )[["user_id", "first_order_date", "customer_city", "customer_state"]]

    order_financials = (
        items.groupby("order_id")
        .agg(
            items_gmv=("price", "sum"),
            freight_value=("freight_value", "sum"),
        )
        .reset_index()
    )

    orders_df = orders_with_users.merge(order_financials, on="order_id", how="left")
    orders_df["items_gmv"] = orders_df["items_gmv"].fillna(0.0).round(2)
    orders_df["freight_value"] = orders_df["freight_value"].fillna(0.0).round(2)

    orders_clean = orders_df[
        [
            "order_id",
            "customer_unique_id",
            "order_status",
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "items_gmv",
            "freight_value",
        ]
    ].rename(
        columns={
            "customer_unique_id": "user_id",
            "order_purchase_timestamp": "created_at",
            "order_delivered_customer_date": "delivered_at",
        }
    )

    valid_order_ids = set(orders_clean["order_id"])
    items_clean = items[items["order_id"].isin(valid_order_ids)][
        ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"]
    ].copy()

    schema_path = os.path.join(SQL_DIR, "00_init_schema.sql")
    with engine.begin() as conn:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.execute(text(f.read()))

    with engine.begin() as conn:
        users_df.to_sql("users", conn, if_exists="append", index=False, method=psql_insert_copy)
        orders_clean.to_sql("orders", conn, if_exists="append", index=False, method=psql_insert_copy)
        items_clean.to_sql("order_items", conn, if_exists="append", index=False, method=psql_insert_copy)

    sql_files = [
        ("01_daily_metrics.sql", "daily_metrics.csv"),
        ("02_monthly_metrics.sql", "monthly_metrics.csv"),
        ("03_cohort_retention.sql", "cohort_retention.csv"),
    ]

    with engine.connect() as conn:
        for sql_file, csv_file in sql_files:
            sql_path = os.path.join(SQL_DIR, sql_file)
            out_path = os.path.join(REPORTS_DIR, csv_file)
            with open(sql_path, "r", encoding="utf-8") as f:
                query = f.read()
            df_res = pd.read_sql_query(text(query), conn)
            df_res.to_csv(out_path, index=False)


if __name__ == "__main__":
    main()