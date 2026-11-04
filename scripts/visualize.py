import os
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
OUTPUT_IMG_DIR = os.path.join(REPORTS_DIR, "img")
os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

monthly_path = os.path.join(REPORTS_DIR, "monthly_metrics.csv")
if os.path.exists(monthly_path):
    monthly_df = pd.read_csv(monthly_path)
    monthly_df["sales_month"] = pd.to_datetime(monthly_df["sales_month"])

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()

    gmv_col = "monthly_gmv" if "monthly_gmv" in monthly_df.columns else "monthly_revenue"

    ax1.bar(
        monthly_df["sales_month"],
        monthly_df[gmv_col] / 1e6,
        width=20,
        color="#2b5c8f",
        alpha=0.85,
        label="Товарный GMV (млн BRL)",
    )
    ax2.plot(
        monthly_df["sales_month"],
        monthly_df["monthly_active_buyers"],
        color="#d95f02",
        marker="o",
        linewidth=2,
        label="Покупатели в месяц",
    )

    ax1.set_ylabel("GMV без учета доставки, млн BRL", color="#2b5c8f")
    ax2.set_ylabel("Активные покупатели в месяц", color="#d95f02")
    ax1.set_title("Olist: Динамика GMV и активных покупателей (янв 2017 – авг 2018)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_IMG_DIR, "monthly_dynamics.png"), dpi=200)
    plt.close(fig)
    print("✓ График динамики сохранен: monthly_dynamics.png")

cohort_path = os.path.join(REPORTS_DIR, "cohort_retention.csv")
if os.path.exists(cohort_path):
    cohort_df = pd.read_csv(cohort_path)
    cohort_df["cohort_label"] = (
        pd.to_datetime(cohort_df["cohort_month"]).dt.strftime("%Y-%m")
        + " (n="
        + cohort_df["cohort_size"].astype(str)
        + ")"
    )
    cohort_df = cohort_df.set_index("cohort_label")

    pct_cols = [f"m{i}_pct" for i in range(1, 7)]
    user_cols = [f"m{i}_users" for i in range(1, 7)]

    heatmap_data = cohort_df[pct_cols]

    annot_matrix = np.empty(heatmap_data.shape, dtype=object)
    for i in range(heatmap_data.shape[0]):
        for j in range(heatmap_data.shape[1]):
            pct_val = cohort_df[pct_cols[j]].iloc[i]
            usr_val = cohort_df[user_cols[j]].iloc[i]
            if pd.isna(pct_val):
                annot_matrix[i, j] = ""
            else:
                annot_matrix[i, j] = f"{pct_val:.2f}%\n({int(usr_val)})"

    plt.figure(figsize=(11, 8))
    ax = sns.heatmap(
        heatmap_data,
        annot=annot_matrix,
        fmt="",
        cmap="Blues",
        cbar=True,
        vmin=0,
        vmax=0.8,
        annot_kws={"size": 8},
        linewidths=0.5,
        linecolor="#e0e0e0",
    )
    ax.set_facecolor("#f0f0f0")
    ax.set_xticklabels([f"M{i}" for i in range(1, 7)])
    plt.title("Когортный Retention Rate: % возврата и число клиентов (серый = конец окна данных)")
    plt.xlabel("Месяц жизни когорты (Lifetime)")
    plt.ylabel("Когорта (месяц первой покупки и размер)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_IMG_DIR, "cohort_retention_heatmap.png"), dpi=200)
    plt.close()
    print("✓ Тепловая карта сохранена: cohort_retention_heatmap.png")

rfm_path = os.path.join(REPORTS_DIR, "rfm_segments_summary.csv")
if os.path.exists(rfm_path):
    rfm_summary = pd.read_csv(rfm_path)

    target_gmv_col = None
    for candidate in ["gmv_share_pct", "monetary_share_pct", "revenue_share_pct", "pct_monetary"]:
        if candidate in rfm_summary.columns:
            target_gmv_col = candidate
            break

    target_users_col = None
    for candidate in ["users_share_pct", "customers_share_pct", "user_share_pct", "pct_customers"]:
        if candidate in rfm_summary.columns:
            target_users_col = candidate
            break

    segment_col = "segment" if "segment" in rfm_summary.columns else rfm_summary.columns[0]

    if target_gmv_col and target_users_col:
        rfm_summary = rfm_summary.sort_values(by=target_gmv_col, ascending=True)

        fig, ax = plt.subplots(figsize=(10, 5.5))
        y_positions = range(len(rfm_summary))
        width = 0.38

        ax.barh(
            [p - width / 2 for p in y_positions],
            rfm_summary[target_users_col],
            width,
            label="Доля клиентов (%)",
            color="#a6bddb",
        )
        ax.barh(
            [p + width / 2 for p in y_positions],
            rfm_summary[target_gmv_col],
            width,
            label="Доля GMV (%)",
            color="#02818a",
        )

        ax.set_yticks(y_positions)
        ax.set_yticklabels(rfm_summary[segment_col])
        ax.set_xlabel("Доля от общего итога (%)")
        ax.set_title("RFM-сегменты: Доля клиентской базы vs Вклад в товарный GMV")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_IMG_DIR, "rfm_segments.png"), dpi=200)
        plt.close()
        print("✓ Диаграмма сегментов сохранена: rfm_segments.png")
    else:
        print(f"! Внимание: в файле rfm_segments_summary.csv найдены колонки: {list(rfm_summary.columns)}")