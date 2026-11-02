WITH user_orders AS (
    SELECT 
        user_id,
        DATE_TRUNC('month', created_at)::DATE AS order_month,
        MIN(DATE_TRUNC('month', created_at)::DATE) OVER (PARTITION BY user_id) AS cohort_month
    FROM orders
    WHERE status != 'canceled'
),
cohort_lifetimes AS (
    SELECT DISTINCT
        user_id,
        cohort_month,
        order_month,
        (EXTRACT(YEAR FROM order_month) - EXTRACT(YEAR FROM cohort_month)) * 12 +
        (EXTRACT(MONTH FROM order_month) - EXTRACT(MONTH FROM cohort_month)) AS month_number
    FROM user_orders
),
cohort_sizes AS (
    SELECT 
        cohort_month,
        COUNT(DISTINCT user_id) AS initial_users
    FROM cohort_lifetimes
    WHERE month_number = 0
    GROUP BY cohort_month
),
retention_counts AS (
    SELECT 
        cohort_month,
        month_number,
        COUNT(DISTINCT user_id) AS active_users
    FROM cohort_lifetimes
    GROUP BY cohort_month, month_number
)
SELECT 
    r.cohort_month,
    s.initial_users AS cohort_size,
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
