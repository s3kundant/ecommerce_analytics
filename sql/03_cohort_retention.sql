WITH all_delivered_orders AS (
    SELECT DISTINCT
        user_id,
        DATE_TRUNC('month', created_at)::date AS order_month
    FROM orders
    WHERE order_status = 'delivered'
      AND created_at < '2018-09-01'
),
user_cohorts AS (
    SELECT
        user_id,
        order_month,
        MIN(order_month) OVER (PARTITION BY user_id) AS cohort_month
    FROM all_delivered_orders
),
filtered_cohorts AS (
    SELECT *
    FROM user_cohorts
    WHERE cohort_month >= '2017-01-01'
      AND cohort_month < '2018-08-01'
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT user_id) AS cohort_size
    FROM filtered_cohorts
    GROUP BY 1
),
retention_raw AS (
    SELECT
        c.cohort_month,
        cs.cohort_size,
        COUNT(DISTINCT CASE 
            WHEN (EXTRACT(YEAR FROM c.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12 +
                 (EXTRACT(MONTH FROM c.order_month) - EXTRACT(MONTH FROM c.cohort_month)) = 1 
            THEN c.user_id END) AS m1_users,
        COUNT(DISTINCT CASE 
            WHEN (EXTRACT(YEAR FROM c.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12 +
                 (EXTRACT(MONTH FROM c.order_month) - EXTRACT(MONTH FROM c.cohort_month)) = 2 
            THEN c.user_id END) AS m2_users,
        COUNT(DISTINCT CASE 
            WHEN (EXTRACT(YEAR FROM c.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12 +
                 (EXTRACT(MONTH FROM c.order_month) - EXTRACT(MONTH FROM c.cohort_month)) = 3 
            THEN c.user_id END) AS m3_users,
        COUNT(DISTINCT CASE 
            WHEN (EXTRACT(YEAR FROM c.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12 +
                 (EXTRACT(MONTH FROM c.order_month) - EXTRACT(MONTH FROM c.cohort_month)) = 4 
            THEN c.user_id END) AS m4_users,
        COUNT(DISTINCT CASE 
            WHEN (EXTRACT(YEAR FROM c.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12 +
                 (EXTRACT(MONTH FROM c.order_month) - EXTRACT(MONTH FROM c.cohort_month)) = 5 
            THEN c.user_id END) AS m5_users,
        COUNT(DISTINCT CASE 
            WHEN (EXTRACT(YEAR FROM c.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12 +
                 (EXTRACT(MONTH FROM c.order_month) - EXTRACT(MONTH FROM c.cohort_month)) = 6 
            THEN c.user_id END) AS m6_users
    FROM filtered_cohorts c
    JOIN cohort_sizes cs ON c.cohort_month = cs.cohort_month
    GROUP BY 1, 2
)
SELECT
    cohort_month,
    cohort_size,
    CASE WHEN cohort_month + INTERVAL '1 month' <= '2018-08-01' THEN m1_users ELSE NULL END AS m1_users,
    CASE WHEN cohort_month + INTERVAL '2 months' <= '2018-08-01' THEN m2_users ELSE NULL END AS m2_users,
    CASE WHEN cohort_month + INTERVAL '3 months' <= '2018-08-01' THEN m3_users ELSE NULL END AS m3_users,
    CASE WHEN cohort_month + INTERVAL '4 months' <= '2018-08-01' THEN m4_users ELSE NULL END AS m4_users,
    CASE WHEN cohort_month + INTERVAL '5 months' <= '2018-08-01' THEN m5_users ELSE NULL END AS m5_users,
    CASE WHEN cohort_month + INTERVAL '6 months' <= '2018-08-01' THEN m6_users ELSE NULL END AS m6_users,
    CASE WHEN cohort_month + INTERVAL '1 month' <= '2018-08-01'
         THEN ROUND(m1_users * 100.0 / cohort_size, 2) ELSE NULL END AS m1_pct,
    CASE WHEN cohort_month + INTERVAL '2 months' <= '2018-08-01'
         THEN ROUND(m2_users * 100.0 / cohort_size, 2) ELSE NULL END AS m2_pct,
    CASE WHEN cohort_month + INTERVAL '3 months' <= '2018-08-01'
         THEN ROUND(m3_users * 100.0 / cohort_size, 2) ELSE NULL END AS m3_pct,
    CASE WHEN cohort_month + INTERVAL '4 months' <= '2018-08-01'
         THEN ROUND(m4_users * 100.0 / cohort_size, 2) ELSE NULL END AS m4_pct,
    CASE WHEN cohort_month + INTERVAL '5 months' <= '2018-08-01'
         THEN ROUND(m5_users * 100.0 / cohort_size, 2) ELSE NULL END AS m5_pct,
    CASE WHEN cohort_month + INTERVAL '6 months' <= '2018-08-01'
         THEN ROUND(m6_users * 100.0 / cohort_size, 2) ELSE NULL END AS m6_pct
FROM retention_raw
ORDER BY cohort_month;