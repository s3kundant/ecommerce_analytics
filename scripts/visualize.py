import os
import matplotlib
matplotlib.use("Agg")

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
OUTPUT_IMG_DIR = os.path.join(REPORTS_DIR, "img")
os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

def find_file(pattern: str) -> str:
    """Ищет файл в папке reports по подстроке имени."""
    for f in os.listdir(REPORTS_DIR):
        if pattern in f and f.endswith(".csv"):
            return os.path.join(REPORTS_DIR, f)
    raise FileNotFoundError(f"Файл, содержащий '{pattern}', не найден в {REPORTS_DIR}")


monthly_path = find_file("monthly_metrics")
monthly_df = pd.read_csv(monthly_path)
monthly_df["sales_month"] = pd.to_datetime(monthly_df["sales_month"])

fig, ax1 = plt.subplots(figsize=(10, 5))
ax2 = ax1.twinx()

ax1.bar(monthly_df["sales_month"], monthly_df["monthly_revenue"] / 1e6, width=20, color="#2b5c8f", alpha=0.8, label="Выручка (млн R$)")
ax2.plot(monthly_df["sales_month"], monthly_df["mau"], color="#d95f02", marker="o", linewidth=2, label="MAU")

ax1.set_ylabel("Выручка, млн BRL", color="#2b5c8f")
ax2.set_ylabel("Активные пользователи в месяц (MAU)", color="#d95f02")
ax1.set_title("Olist: Динамика выручки и MAU (2016-2018)")
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_IMG_DIR, "monthly_dynamics.png"), dpi=200)
plt.close(fig)


cohort_path = find_file("cohort_retention")
cohort_df = pd.read_csv(cohort_path)
cohort_df["cohort_month"] = pd.to_datetime(cohort_df["cohort_month"]).dt.strftime("%Y-%m")
cohort_df.set_index("cohort_month", inplace=True)

retention_cols = [c for c in cohort_df.columns if c.startswith("m") and c.endswith("_pct") and c != "m0_pct"]
heatmap_data = cohort_df[retention_cols]

plt.figure(figsize=(9, 6))
sns.heatmap(heatmap_data, annot=True, fmt=".2f", cmap="Blues", cbar=True, vmin=0, vmax=1.0)
plt.title("Olist: Когортное удержание (Retention Rate, %) с 1 по 6 месяц")
plt.xlabel("Месяц жизни когорты (Lifetime)")
plt.ylabel("Месяц когорты")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_IMG_DIR, "cohort_retention_heatmap.png"), dpi=200)
plt.close()


rfm_path = find_file("rfm_segments_summary")
rfm_summary = pd.read_csv(rfm_path)
rfm_summary = rfm_summary.sort_values(by="revenue_share_pct", ascending=True)

fig, ax = plt.subplots(figsize=(10, 5))
y_positions = range(len(rfm_summary))
width = 0.35

ax.barh([p - width/2 for p in y_positions], rfm_summary["users_share_pct"], width, label="Доля клиентов (%)", color="#a6bddb")
ax.barh([p + width/2 for p in y_positions], rfm_summary["revenue_share_pct"], width, label="Доля выручки (%)", color="#02818a")

ax.set_yticks(y_positions)
ax.set_yticklabels(rfm_summary["segment"])
ax.set_xlabel("Процент от общего итога (%)")
ax.set_title("RFM-сегменты: Доля базы vs Вклад в выручку")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_IMG_DIR, "rfm_segments.png"), dpi=200)
plt.close()

print("Графики успешно сгенерированы в reports/img/")