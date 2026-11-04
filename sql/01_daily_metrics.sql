WITH calendar AS (
    SELECT generate_series(
        '2017-01-01'::date,
        '2018-08-31'::date,
        '1 day'::interval
    )::date AS report_date
),
daily_agg AS (
    SELECT
        created_at::date AS report_date,
        COUNT(DISTINCT user_id) AS daily_buyers,
        COUNT(DISTINCT order_id) AS delivered_orders,
        SUM(items_gmv) AS daily_gmv,
        SUM(items_gmv + freight_value) AS daily_gmv_with_freight
    FROM orders
    WHERE order_status = 'delivered'
      AND created_at >= '2017-01-01'
      AND created_at < '2018-09-01'
    GROUP BY 1
)
SELECT
    c.report_date,
    COALESCE(d.daily_buyers, 0) AS daily_buyers,
    COALESCE(d.delivered_orders, 0) AS delivered_orders,
    COALESCE(d.daily_gmv, 0.00) AS daily_gmv,
    COALESCE(d.daily_gmv_with_freight, 0.00) AS daily_gmv_with_freight,
    ROUND(COALESCE(d.daily_gmv / NULLIF(d.delivered_orders, 0), 0), 2) AS aov,
    ROUND(AVG(COALESCE(d.daily_gmv, 0)) OVER (
        ORDER BY c.report_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_gmv
FROM calendar c
LEFT JOIN daily_agg d ON c.report_date = d.report_date
ORDER BY c.report_date;