"""
RFM-сегментация клиентской базы маркетплейса Olist.
Метрики:
- Recency (R): Давность последней покупки (в днях от даты среза).
- Frequency (F): Общее количество успешных заказов клиента за всё время.
- Monetary (M): Суммарная выручка (LTV), которую принес клиент.
"""

import os
import pandas as pd
import numpy as np
from datetime import timedelta


def load_and_merge_raw_data(data_dir: str = "data") -> pd.DataFrame:
    """
    ШАГ 1: Загрузка и объединение сырых таблиц Olist.
    Нам нужны 3 таблицы:
    1. customers — чтобы достать реальный уникальный ID человека (customer_unique_id).
    2. orders — чтобы получить дату покупки и отфильтровать отмененные заказы.
    3. order_items — чтобы посчитать стоимость товаров и доставки.
    """
    print("[1/5] Загрузка сырых CSV-файлов...")
    
    customers_path = os.path.join(data_dir, "olist_customers_dataset.csv")
    orders_path = os.path.join(data_dir, "olist_orders_dataset.csv")
    items_path = os.path.join(data_dir, "olist_order_items_dataset.csv")

    customers = pd.read_csv(customers_path, usecols=["customer_id", "customer_unique_id"])
    orders = pd.read_csv(
        orders_path, 
        usecols=["order_id", "customer_id", "order_status", "order_purchase_timestamp"]
    )
    items = pd.read_csv(
        items_path, 
        usecols=["order_id", "price", "freight_value"]
    )

    print("[2/5] Очистка и объединение таблиц...")
    
    # Оставляем только успешные транзакции (исключаем отмененные и недоступные)
    valid_statuses = ["delivered", "shipped", "invoiced", "processing", "approved"]
    orders = orders[orders["order_status"].isin(valid_statuses)].copy()

    # Переводим строковую дату в формат datetime
    orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"])

    # Считаем полную сумму каждого чека (цена товара + стоимость доставки)
    items["total_item_value"] = items["price"] + items["freight_value"]
    order_Totals = (
        items.groupby("order_id", as_index=False)["total_item_value"]
        .sum()
        .rename(columns={"total_item_value": "order_amount"})
    )

    # Собираем единую витрину транзакций через INNER JOIN (merge)
    df = (
        orders
        .merge(customers, on="customer_id", how="inner")
        .merge(order_Totals, on="order_id", how="inner")
    )

    return df


def calculate_rfm_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    ШАГ 2: Агрегация данных на уровень уникального клиента и расчет R, F, M.
    """
    print("[3/5] Расчет базовых показателей Recency, Frequency, Monetary...")

    # В исторических датасетах нельзя брать datetime.now()!
    # Мы берем максимальную дату покупки в датасете + 1 день как "точку отсчета" (snapshot_date)
    snapshot_date = df["order_purchase_timestamp"].max() + timedelta(days=1)
    print(f"      Дата среза аналитики (Snapshot Date): {snapshot_date.strftime('%Y-%m-%d')}")

    # Группируем по реальному ID покупателя (customer_unique_id)
    rfm = df.groupby("customer_unique_id", as_index=False).agg(
        # Recency: разница в днях между датой среза и самой последней покупкой клиента
        recency=("order_purchase_timestamp", lambda x: (snapshot_date - x.max()).days),
        # Frequency: количество уникальных заказов клиента
        frequency=("order_id", "nunique"),
        # Monetary: сумма денег по всем заказам клиента
        monetary=("order_amount", "sum")
    )

    # Округляем денежную метрику до 2 знаков после запятой
    rfm["monetary"] = rfm["monetary"].round(2)

    return rfm


def assign_rfm_scores(rfm: pd.DataFrame) -> pd.DataFrame:
    """
    ШАГ 3: Присвоение рангов (баллов от 1 до 5) по каждой метрике.
    - Для Recency: чем МЕНЬШЕ дней прошло, тем ВЫШЕ балл (5 — покупал недавно, 1 — давно).
    - Для Frequency и Monetary: чем БОЛЬШЕ покупок/денег, тем ВЫШЕ балл (5 — максимум).
    """
    print("[4/5] Присвоение RFM-баллов (квантильное разбиение 1-5)...")

    # 1. Оценка Recency (обратная шкала: [5, 4, 3, 2, 1])
    rfm["r_score"] = pd.qcut(
        rfm["recency"], 
        q=5, 
        labels=[5, 4, 3, 2, 1]
    ).astype(int)

    # 2. Оценка Monetary (прямая шкала: [1, 2, 3, 4, 5])
    # Используем .rank(method='first') на случай одинаковых сумм чеков на границах квантилей
    rfm["m_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"), 
        q=5, 
        labels=[1, 2, 3, 4, 5]
    ).astype(int)

    # 3. Оценка Frequency (кастомное правило для e-commerce с низкой частотностью)
    # Так как ~97% пользователей в Olist купили 1 раз, qcut упадет с ошибкой дубликатов границ.
    # Вводим честную бизнес-шкалу: 1 заказ = 1 балл, 2 заказа = 3 балла, 3+ заказов = 5 баллов (VIP по частоте)
    conditions = [
        rfm["frequency"] == 1,
        rfm["frequency"] == 2,
        rfm["frequency"] >= 3
    ]
    choices = [1, 3, 5]
    rfm["f_score"] = np.select(conditions, choices, default=1)

    # Формируем строковый RFM-индекс (например, "555" или "112") для наглядности
    rfm["rfm_score_str"] = (
        rfm["r_score"].astype(str) + 
        rfm["f_score"].astype(str) + 
        rfm["m_score"].astype(str)
    )

    return rfm


def map_rfm_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    """
    ШАГ 4: Разметка бизнес-сегментов на основе матрицы R и M/F баллов.
    """
    print("[5/5] Сегментация пользователей по бизнес-группам...")

    def get_segment(row):
        r = row["r_score"]
        f = row["f_score"]
        m = row["m_score"]

        # 1. Champions (Чемпионы): покупали недавно (R>=4), делают повторные заказы (F>=3) и платят много (M>=4)
        if r >= 4 and f >= 3 and m >= 4:
            return "Champions (Чемпионы)"
        
        # 2. Loyal Customers (Лояльные): совершили более 1 покупки и недавно были активны (R>=3, F>=3)
        elif r >= 3 and f >= 3:
            return "Loyal Customers (Постоянные)"
        
        # 3. Big Spenders / Whales (Киты / Крупные чеки): купили 1 раз, но недавно и на крупную сумму (R>=4, M>=4)
        elif r >= 4 and m >= 4:
            return "Promising Whales (Крупные новички)"
        
        # 4. New Customers (Новички): купили совсем недавно (R>=4), но чек пока небольшой/средний (M<=3)
        elif r >= 4 and m <= 3:
            return "Recent Customers (Свежие клиенты)"
        
        # 5. Potential Loyalists (Потенциальные): средняя давность (R=3), хороший чек (M>=3)
        elif r == 3 and m >= 3:
            return "Need Attention (Требуют внимания)"
        
        # 6. Cant Lose Them (Нельзя терять): раньше покупали повторно или на огромные чеки (F>=3 или M=5), но давно не заходили (R<=2)
        elif r <= 2 and (f >= 3 or m == 5):
            return "Can't Lose Them (VIP в зоне риска)"
        
        # 7. At Risk (В зоне оттока): покупали давно (R=2), средний чек (M от 2 до 4)
        elif r == 2 and m >= 2:
            return "At Risk (Уходящие)"
        
        # 8. Hibernating / Lost (Потерянные / Спящие): покупали очень давно (R=1) и на малые суммы
        else:
            return "Lost / Hibernating (Потерянные)"

    rfm["segment"] = rfm.apply(get_segment, axis=1)
    return rfm


def generate_summary_report(rfm: pd.DataFrame, output_dir: str = "reports"):
    """
    ШАГ 5: Создание сводной таблицы по сегментам и сохранение CSV-файлов.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Сводная статистика по каждому сегменту для дашборда и README
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

    # Считаем долю пользователей и долю выручки каждого сегмента в %
    summary["users_share_pct"] = (summary["users_count"] / summary["users_count"].sum() * 100).round(2)
    summary["revenue_share_pct"] = (summary["total_revenue"] / summary["total_revenue"].sum() * 100).round(2)
    summary["avg_recency_days"] = summary["avg_recency_days"].round(1)
    summary["avg_frequency"] = summary["avg_frequency"].round(2)
    summary["avg_monetary"] = summary["avg_monetary"].round(2)
    summary["total_revenue"] = summary["total_revenue"].round(2)

    # Сортируем по вкладу в общую выручку
    summary = summary.sort_values(by="total_revenue", ascending=False)

    # Сохраняем детальную разметку каждого клиента и сводную таблицу по сегментам
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
    # Запускаем весь пайплайн последовательно
    raw_df = load_and_merge_raw_data(data_dir="data")
    rfm_df = calculate_rfm_metrics(raw_df)
    rfm_scored = assign_rfm_scores(rfm_df)
    rfm_segmented = map_rfm_segments(rfm_scored)
    generate_summary_report(rfm_segmented, output_dir="reports")