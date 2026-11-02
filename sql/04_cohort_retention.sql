WITH user_orders AS (
    -- ШАГ 1: Очистка данных и определение когорты каждого пользователя через оконную функцию
    SELECT 
        user_id,
        -- Приводим дату текущего заказа к первому числу месяца (например, 2017-05-14 -> 2017-05-01)
        DATE_TRUNC('month', created_at)::DATE AS order_month,
        -- ОКОННАЯ ФУНКЦИЯ: находим самый первый месяц покупки для конкретного user_id
        MIN(DATE_TRUNC('month', created_at)::DATE) OVER (PARTITION BY user_id) AS cohort_month
    FROM orders
    WHERE status != 'canceled'
),
cohort_lifetimes AS (
    -- ШАГ 2: Дедупликация и расчет "возраста" покупки в месяцах (Lifetime / Month Number)
    SELECT DISTINCT
        user_id,
        cohort_month,
        order_month,
        -- Математика: переводим разницу лет в месяцы и прибавляем разницу месяцев
        (EXTRACT(YEAR FROM order_month) - EXTRACT(YEAR FROM cohort_month)) * 12 +
        (EXTRACT(MONTH FROM order_month) - EXTRACT(MONTH FROM cohort_month)) AS month_number
    FROM user_orders
),
cohort_sizes AS (
    -- ШАГ 3: Считаем изначальный размер каждой когорты (база для расчета процентов в Month 0)
    SELECT 
        cohort_month,
        COUNT(DISTINCT user_id) AS initial_users
    FROM cohort_lifetimes
    WHERE month_number = 0
    GROUP BY cohort_month
),
retention_counts AS (
    -- ШАГ 4: Считаем сколько уникальных клиентов вернулось в каждый последующий месяц
    SELECT 
        cohort_month,
        month_number,
        COUNT(DISTINCT user_id) AS active_users
    FROM cohort_lifetimes
    GROUP BY cohort_month, month_number
)
-- ШАГ 5: Сборка финальной сводной таблицы (Pivot Table) в процентах
SELECT 
    r.cohort_month,
    s.initial_users AS cohort_size,
    -- Разворачиваем строки в колонки через условную агрегацию (CASE WHEN)
    ROUND(MAX(CASE WHEN r.month_number = 0 THEN r.active_users::NUMERIC / s.initial_users * 100 END), 2) AS m0_pct,
    ROUND(MAX(CASE WHEN r.month_number = 1 THEN r.active_users::NUMERIC / s.initial_users * 100 END), 2) AS m1_pct,
    ROUND(MAX(CASE WHEN r.month_number = 2 THEN r.active_users::NUMERIC / s.initial_users * 100 END), 2) AS m2_pct,
    ROUND(MAX(CASE WHEN r.month_number = 3 THEN r.active_users::NUMERIC / s.initial_users * 100 END), 2) AS m3_pct,
    ROUND(MAX(CASE WHEN r.month_number = 4 THEN r.active_users::NUMERIC / s.initial_users * 100 END), 2) AS m4_pct,
    ROUND(MAX(CASE WHEN r.month_number = 5 THEN r.active_users::NUMERIC / s.initial_users * 100 END), 2) AS m5_pct,
    ROUND(MAX(CASE WHEN r.month_number = 6 THEN r.active_users::NUMERIC / s.initial_users * 100 END), 2) AS m6_pct
FROM retention_counts r
JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
WHERE r.cohort_month >= '2017-01-01'
GROUP BY r.cohort_month, s.initial_users
ORDER BY r.cohort_month ASC;