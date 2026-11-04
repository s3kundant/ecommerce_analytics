SELECT
    DATE_TRUNC('month', created_at)::date AS sales_month,
    COUNT(DISTINCT order_id) AS delivered_orders,
    COUNT(DISTINCT user_id) AS monthly_active_buyers,
    ROUND(SUM(items_gmv), 2) AS monthly_gmv,
    ROUND(SUM(freight_value), 2) AS monthly_freight,
    ROUND(SUM(items_gmv + freight_value), 2) AS total_billed_amount,
    ROUND(AVG(items_gmv), 2) AS avg_order_gmv
FROM orders
WHERE order_status = 'delivered'
  AND created_at >= '2017-01-01'
  AND created_at < '2018-09-01'
GROUP BY 1
ORDER BY 1;