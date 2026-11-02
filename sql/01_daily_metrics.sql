WITH daily_metrics AS (
    -- ШАГ 1: Агрегация на уровне календарного дня
    SELECT 
        DATE(created_at) AS order_date,
        COUNT(DISTINCT user_id) AS dau,
        COUNT(order_id) AS daily_orders,
        SUM(CASE WHEN status != 'canceled' THEN 1 ELSE 0 END) AS paid_orders,
        SUM(CASE WHEN status != 'canceled' THEN total_amount ELSE 0 END) AS daily_revenue
    FROM orders
    GROUP BY DATE(created_at)
),
calculated_metrics AS (
    -- ШАГ 2: Расчет AOV и оконные функции
    SELECT 
        order_date,
        dau,
        daily_orders,
        daily_revenue,
        ROUND(daily_revenue / NULLIF(paid_orders, 0), 2) AS daily_aov,
        LAG(dau, 1) OVER (ORDER BY order_date) AS prev_day_dau,
        ROUND(AVG(daily_revenue) OVER (ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS revenue_7d_moving_avg
    FROM daily_metrics
)
-- ШАГ 3: Финальный расчет прироста
SELECT 
    order_date,
    dau,
    daily_orders,
    daily_revenue,
    daily_aov,
    revenue_7d_moving_avg,
    ROUND(((dau - prev_day_dau)::NUMERIC / NULLIF(prev_day_dau, 0)) * 100, 2) AS dau_dod_growth_pct
FROM calculated_metrics
ORDER BY dau DESC;
