import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import csv
from io import StringIO

print(">>> [1/5] Загрузка скрипта и переменных окружения...")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SQL_DIR = os.path.join(BASE_DIR, "sql")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def get_engine():
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db = os.getenv("DB_NAME", "ecommerce_analytics")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    print(f">>> [2/5] Подключение к PostgreSQL: {host}:{port}/{db} (пользователь: {user})...")
    return create_engine(url)


def init_schema(engine):
    schema_path = os.path.join(SQL_DIR, "00_init_schema.sql")
    print(f">>> [3/5] Применение схемы из {schema_path}...")
    if not os.path.exists(schema_path):
        print(f"ОШИБКА: Файл {schema_path} не найден!")
        sys.exit(1)
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_commands = f.read()
    with engine.begin() as conn:
        conn.execute(text(sql_commands))
    print(">>> Схема успешно создана в базе данных.")

def psql_insert_copy(table, conn, keys, data_iter):
    """Сверхбыстрая вставка через COPY вместо построчного INSERT"""
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)
        columns = ', '.join([f'"{k}"' for k in keys])
        table_name = f'"{table.name}"'
        cur.copy_expert(f"COPY {table_name} ({columns}) FROM STDIN WITH CSV", s_buf)

def load_raw_data(engine):
    print(">>> [4/5] Чтение сырых CSV-файлов из data/...")
    cust_path = os.path.join(DATA_DIR, "olist_customers_dataset.csv")
    ord_path = os.path.join(DATA_DIR, "olist_orders_dataset.csv")
    items_path = os.path.join(DATA_DIR, "olist_order_items_dataset.csv")

    customers = pd.read_csv(cust_path)
    orders = pd.read_csv(ord_path)
    items = pd.read_csv(items_path)

    orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"])

    orders_with_uni = orders.merge(
        customers[["customer_id", "customer_unique_id", "customer_city", "customer_state"]],
        on="customer_id",
        how="inner",
    )

    items_agg = (
        items.groupby("order_id", as_index=False)
        .agg(items_gmv=("price", "sum"), freight_value=("freight_value", "sum"))
    )

    orders_full = orders_with_uni.merge(items_agg, on="order_id", how="inner")

    users_df = (
        orders_full.sort_values("order_purchase_timestamp")
        .groupby("customer_unique_id", as_index=False)
        .agg(
            customer_city=("customer_city", "first"),
            customer_state=("customer_state", "first"),
            first_order_date=("order_purchase_timestamp", "min"),
        )
        .rename(columns={"customer_unique_id": "user_id"})
    )

    orders_db = orders_full[
        ["order_id", "customer_unique_id", "order_status", "order_purchase_timestamp", "items_gmv", "freight_value"]
    ].rename(
        columns={
            "customer_unique_id": "user_id",
            "order_purchase_timestamp": "created_at",
        }
    )

    valid_order_ids = set(orders_db["order_id"])
    items_db = items[items["order_id"].isin(valid_order_ids)][
        ["order_id", "product_id", "price", "freight_value"]
    ].copy()

    print(">>> Быстрая заливка users в PostgreSQL...")
    users_df.to_sql("users", engine, if_exists="append", index=False, method=psql_insert_copy)
    print(">>> Быстрая заливка orders в PostgreSQL...")
    orders_db.to_sql("orders", engine, if_exists="append", index=False, method=psql_insert_copy)
    print(">>> Быстрая заливка order_items в PostgreSQL...")
    items_db.to_sql("order_items", engine, if_exists="append", index=False, method=psql_insert_copy)
    print(">>> Все таблицы успешно заполнены за несколько секунд.")


def export_sql_marts(engine):
    print(">>> [5/5] Выполнение SQL-запросов и экспорт витрин в reports/...")
    sql_files = {
        "01_daily_metrics.sql": "daily_metrics.csv",
        "02_monthly_metrics.sql": "monthly_metrics.csv",
        "03_cohort_retention.sql": "cohort_retention.csv",
    }
    for sql_file, csv_name in sql_files.items():
        path = os.path.join(SQL_DIR, sql_file)
        if not os.path.exists(path):
            print(f"ОШИБКА: SQL-файл {path} не найден!")
            continue
        print(f"    - Обработка {sql_file} -> {csv_name}...")
        with open(path, "r", encoding="utf-8") as f:
            query = f.read()
        df = pd.read_sql(query, engine)
        df.to_csv(os.path.join(REPORTS_DIR, csv_name), index=False)



print(">>> Старт выполнения программы...")
eng = get_engine()
init_schema(eng)
load_raw_data(eng)
export_sql_marts(eng)
print(">>> ГОТОВО: База данных обновлена, SQL-витрины выгружены в reports/!")