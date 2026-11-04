import os
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
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def get_engine():
    auth = f"{DB_USER}:{DB_PASSWORD}" if DB_PASSWORD else DB_USER
    db_url = f"postgresql+psycopg2://{auth}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(db_url)


def assign_segment(row):
    r, f = row["r_score"], row["f_score"]
    if r >= 4 and f == 3:
        return "Champions (Лояльные недавние)"
    if r >= 3 and f >= 2:
        return "Loyal / Repeat (Повторные)"
    if r >= 4 and f == 1:
        return "New / Promising (Новые с 1 заказом)"
    if r == 3 and f == 1:
        return "About to Sleep (Остывающие с 1 заказом)"
    if r <= 2 and f >= 2:
        return "At Risk Repeat (Уходящие повторные)"
    return "Hibernating / Lost (Давние с 1 заказом)"


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    engine = get_engine()

    rfm_query = """
    WITH max_date AS (
        SELECT MAX(created_at)::date + INTERVAL '1 day' AS ref_date
        FROM orders
        WHERE order_status = 'delivered'
          AND created_at >= '2017-01-01'
          AND created_at < '2018-09-01'
    )
    SELECT
        o.user_id,
        EXTRACT(DAY FROM (m.ref_date - MAX(o.created_at)))::int AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        ROUND(SUM(o.items_gmv), 2) AS monetary_gmv
    FROM orders o
    CROSS JOIN max_date m
    WHERE o.order_status = 'delivered'
      AND o.created_at >= '2017-01-01'
      AND o.created_at < '2018-09-01'
    GROUP BY o.user_id, m.ref_date;
    """

    with engine.connect() as conn:
        rfm = pd.read_sql_query(text(rfm_query), conn)

    rfm["r_score"] = pd.qcut(rfm["recency_days"], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary_gmv"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["f_score"] = rfm["frequency"].apply(lambda x: 1 if x == 1 else (2 if x == 2 else 3))

    rfm["segment"] = rfm.apply(assign_segment, axis=1)

    total_users = len(rfm)
    total_gmv = rfm["monetary_gmv"].sum()

    summary = (
        rfm.groupby("segment", as_index=False)
        .agg(
            users_count=("user_id", "count"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary_gmv=("monetary_gmv", "mean"),
            total_segment_gmv=("monetary_gmv", "sum"),
        )
    )

    summary["users_share_pct"] = (summary["users_count"] * 100.0 / total_users).round(2)
    summary["gmv_share_pct"] = (summary["total_segment_gmv"] * 100.0 / total_gmv).round(2)
    summary["avg_recency_days"] = summary["avg_recency_days"].round(1)
    summary["avg_frequency"] = summary["avg_frequency"].round(2)
    summary["avg_monetary_gmv"] = summary["avg_monetary_gmv"].round(2)
    summary["total_segment_gmv"] = summary["total_segment_gmv"].round(2)

    summary = summary.sort_values(by="total_segment_gmv", ascending=False)

    out_path = os.path.join(REPORTS_DIR, "rfm_segments_summary.csv")
    summary.to_csv(out_path, index=False)
    print(f"✓ RFM-сегментация успешно рассчитана! Общий GMV = {total_gmv:,.2f} BRL")


if __name__ == "__main__":
    main()
