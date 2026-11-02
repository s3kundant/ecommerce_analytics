WITH monthly_raw AS (
    -- ШАГ 1: Усечение дат до первого числа месяца и группировка
    SELECT 
        -- DATE_TRUNC('month', ...) превращает любую дату (2018-05-14) в начало месяца (2018-05-01 00:00:00)
        DATE_TRUNC('month', created_at)::DATE AS sales_month,        
        -- Уникальные клиенты за весь месяц (MAU)
        COUNT(DISTINCT user_id) AS mau,        
        -- Общее число закрытых заказов за месяц
        COUNT(order_id) FILTER (WHERE status != 'canceled') AS paid_orders,        
        -- Месячный оборот
        ROUND(SUM(total_amount) FILTER (WHERE status != 'canceled'), 2) AS monthly_revenue
    FROM orders
    GROUP BY DATE_TRUNC('month', created_at)
),
monthly_analytics AS (
    -- ШАГ 2: Оконные функции поверх месячных агрегатов
    SELECT 
        sales_month,
        mau,
        paid_orders,
        monthly_revenue,        
        -- Расчет месячного AOV
        ROUND(monthly_revenue / NULLIF(paid_orders, 0), 2) AS monthly_aov,     
        -- ОКОННАЯ ФУНКЦИЯ 1: Выручка предыдущего календарного месяца
        LAG(monthly_revenue, 1) OVER (ORDER BY sales_month) AS prev_month_revenue,        
        -- ОКОННАЯ ФУНКЦИЯ 2: Накопительный итог выручки (Running Total) от начала истории
        -- Без указания фрейма по умолчанию берется диапазон: UNBOUNDED PRECEDING AND CURRENT ROW
        SUM(monthly_revenue) OVER (ORDER BY sales_month) AS cumulative_revenue,   
        -- ОКОННАЯ ФУНКЦИЯ 3: Средний MAU за предыдущие 3 месяца (квартальный тренд)
        ROUND(
            AVG(mau) OVER (
                ORDER BY sales_month 
                ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
            ), 0
        ) AS avg_mau_prev_quarter
    FROM monthly_raw
)
-- ШАГ 3: Финальный расчет Month-over-Month динамики
SELECT 
    sales_month,
    mau,
    paid_orders,
    monthly_revenue,
    monthly_aov,
    cumulative_revenue,    
    -- Прирост выручки к предыдущему месяцу (MoM Revenue Growth)
    ROUND(
        ((monthly_revenue - prev_month_revenue) / NULLIF(prev_month_revenue, 0)) * 100, 2
    ) AS mom_revenue_growth_pct,    
    -- Динамика MAU относительно среднего за прошлый квартал
    ROUND(
        ((mau - avg_mau_prev_quarter) / NULLIF(avg_mau_prev_quarter, 0)) * 100, 2
    ) AS mau_vs_prev_quarter_pct
FROM monthly_analytics
ORDER BY sales_month ASC;