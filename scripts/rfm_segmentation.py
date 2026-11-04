import os
import logging
from datetime import timedelta
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

VALID_STATUSES = ["delivered", "shipped", "invoiced", "processing", "approved"]


<<<<<<< HEAD
def load_and_merge_raw_data(data_dir: str = "data") -> pd.DataFrame:
    print("[1/5] Загрузка сырых CSV-файлов...")
    
    customers_path = os.path.join(data_dir, "olist_customers_dataset.csv")
    orders_path = os.path.join(data_dir, "olist_orders_dataset.csv")
    items_path = os.path.join(data_dir, "olist_order_items_dataset.csv")

    customers = pd.read_csv(customers_path, usecols=["customer_id", "customer_unique_id"])
=======
def load_transactions(data_dir: str = "data") -> pd.DataFrame:
    customers = pd.read_csv(
        os.path.join(data_dir, "olist_customers_dataset.csv"),
        usecols=["customer_id", "customer_unique_id"]
    )
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)
    orders = pd.read_csv(
        os.path.join(data_dir, "olist_orders_dataset.csv"),
        usecols=["order_id", "customer_id", "order_status", "order_purchase_timestamp"]
    )
    items = pd.read_csv(
        os.path.join(data_dir, "olist_order_items_dataset.csv"),
        usecols=["order_id", "price", "freight_value"]
    )

<<<<<<< HEAD
    print("[2/5] Очистка и объединение таблиц...")
    
    valid_statuses = ["delivered", "shipped", "invoiced", "processing", "approved"]
    orders = orders[orders["order_status"].isin(valid_statuses)].copy()

    orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"])

    items["total_item_value"] = items["price"] + items["freight_value"]
    order_Totals = (
        items.groupby("order_id", as_index=False)["total_item_value"]
        .sum()
        .rename(columns={"total_item_value": "order_amount"})
    )
=======
    orders = orders[orders["order_status"].isin(VALID_STATUSES)].copy()
    orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"])

    items["order_amount"] = items["price"] + items["freight_value"]
    order_totals = items.groupby("order_id", as_index=False)["order_amount"].sum()
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)

    df = (
        orders
        .merge(customers, on="customer_id", how="inner")
        .merge(order_totals, on="order_id", how="inner")
    )
    return df


<<<<<<< HEAD
def calculate_rfm_metrics(df: pd.DataFrame) -> pd.DataFrame:

    print("[3/5] Расчет базовых показателей Recency, Frequency, Monetary...")

=======
def build_rfm_table(df: pd.DataFrame) -> pd.DataFrame:
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)
    snapshot_date = df["order_purchase_timestamp"].max() + timedelta(days=1)
    logging.info(f"Snapshot date set to {snapshot_date.strftime('%Y-%m-%d')}")

    rfm = df.groupby("customer_unique_id", as_index=False).agg(
        recency=("order_purchase_timestamp", lambda x: (snapshot_date - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("order_amount", "sum")
    )
<<<<<<< HEAD

=======
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)
    rfm["monetary"] = rfm["monetary"].round(2)

    rfm["r_score"] = pd.qcut(rfm["recency"], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]).astype(int)

<<<<<<< HEAD

def assign_rfm_scores(rfm: pd.DataFrame) -> pd.DataFrame:

    print("[4/5] Присвоение RFM-баллов (квантильное разбиение 1-5)...")

    rfm["r_score"] = pd.qcut(
        rfm["recency"], 
        q=5, 
        labels=[5, 4, 3, 2, 1]
    ).astype(int)

    rfm["m_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"), 
        q=5, 
        labels=[1, 2, 3, 4, 5]
    ).astype(int)

    conditions = [
        rfm["frequency"] == 1,
        rfm["frequency"] == 2,
        rfm["frequency"] >= 3
    ]
    choices = [1, 3, 5]
    rfm["f_score"] = np.select(conditions, choices, default=1)

    rfm["rfm_score_str"] = (
        rfm["r_score"].astype(str) + 
        rfm["f_score"].astype(str) + 
        rfm["m_score"].astype(str)
=======
    # Custom frequency bins due to ~97% single-order distribution in Olist dataset
    rfm["f_score"] = np.select(
        [rfm["frequency"] == 1, rfm["frequency"] == 2, rfm["frequency"] >= 3],
        [1, 3, 5],
        default=1
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)
    )

    rfm["rfm_score"] = (
        rfm["r_score"].astype(str) +
        rfm["f_score"].astype(str) +
        rfm["m_score"].astype(str)
    )
    return rfm


<<<<<<< HEAD
def map_rfm_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    
    print("[5/5] Сегментация пользователей по бизнес-группам...")

    def get_segment(row):
        r = row["r_score"]
        f = row["f_score"]
        m = row["m_score"]

        if r >= 4 and f >= 3 and m >= 4:
            return "Champions (Чемпионы)"
        
        elif r >= 3 and f >= 3:
            return "Loyal Customers (Постоянные)"
        
        elif r >= 4 and m >= 4:
            return "Promising Whales (Крупные новички)"
        
        elif r >= 4 and m <= 3:
            return "Recent Customers (Свежие клиенты)"
        
        elif r == 3 and m >= 3:
            return "Need Attention (Требуют внимания)"
        
        elif r <= 2 and (f >= 3 or m == 5):
            return "Can't Lose Them (VIP в зоне риска)"
        
        elif r == 2 and m >= 2:
            return "At Risk (Уходящие)"
        
        else:
            return "Lost / Hibernating (Потерянные)"
=======
def assign_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    def _segment_mapper(row):
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 4 and f >= 3 and m >= 4:
            return "Champions"
        elif r >= 3 and f >= 3:
            return "Loyal Customers"
        elif r >= 4 and m >= 4:
            return "Promising Whales"
        elif r >= 4 and m <= 3:
            return "Recent Customers"
        elif r == 3 and m >= 3:
            return "Need Attention"
        elif r <= 2 and (f >= 3 or m == 5):
            return "Can't Lose Them"
        elif r == 2 and m >= 2:
            return "At Risk"
        return "Lost / Hibernating"
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)

    rfm["segment"] = rfm.apply(_segment_mapper, axis=1)
    return rfm


<<<<<<< HEAD
def generate_summary_report(rfm: pd.DataFrame, output_dir: str = "reports"):

=======
def export_reports(rfm: pd.DataFrame, output_dir: str = "reports") -> None:
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)
    os.makedirs(output_dir, exist_ok=True)

    summary = (
        rfm.groupby("segment", as_index=False)
        .agg(
            users_count=("customer_unique_id", "count"),
            avg_recency_days=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            total_revenue=("monetary", "sum")
        )
    )
<<<<<<< HEAD
=======

>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)
    summary["users_share_pct"] = (summary["users_count"] / summary["users_count"].sum() * 100).round(2)
    summary["revenue_share_pct"] = (summary["total_revenue"] / summary["total_revenue"].sum() * 100).round(2)

<<<<<<< HEAD
    summary = summary.sort_values(by="total_revenue", ascending=False)
    users_output = os.path.join(output_dir, "rfm_users_detailed.csv")
    summary_output = os.path.join(output_dir, "rfm_segments_summary.csv")

    rfm.to_csv(users_output, index=False)
    summary.to_csv(summary_output, index=False)

    print("\n" + "=" * 85)
    print("ИТОГОВАЯ ТАБЛИЦА RFM-СЕГМЕНТАЦИИ:")
    print("=" * 85)
    print(summary.to_string(index=False))
    print("=" * 85)
    print(f"\n[ГОТОВО] Файлы успешно сохранены в папку '{output_dir}/':")
    print(f"  1. {users_output} (полная база клиентов с RFM-рангами)")
    print(f"  2. {summary_output} (сводная аналитика по сегментам для отчета)")


if __name__ == "__main__":
    raw_df = load_and_merge_raw_data(data_dir="data")
    rfm_df = calculate_rfm_metrics(raw_df)
    rfm_scored = assign_rfm_scores(rfm_df)
    rfm_segmented = map_rfm_segments(rfm_scored)
    generate_summary_report(rfm_segmented, output_dir="reports")
=======
    for col in ["avg_recency_days", "avg_frequency", "avg_monetary", "total_revenue"]:
        summary[col] = summary[col].round(2)

    summary = summary.sort_values(by="total_revenue", ascending=False)

    rfm.to_csv(os.path.join(output_dir, "rfm_users_detailed.csv"), index=False)
    summary.to_csv(os.path.join(output_dir, "rfm_segments_summary.csv"), index=False)
    logging.info(f"RFM reports exported to '{output_dir}/'")


if __name__ == "__main__":
    transactions_df = load_transactions()
    rfm_df = build_rfm_table(transactions_df)
    segmented_df = assign_segments(rfm_df)
    export_reports(segmented_df)
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)
