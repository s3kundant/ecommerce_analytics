WITH monthly_raw AS (
    SELECT 
        DATE_TRUNC('month', created_at)::DATE AS sales_month,        
        COUNT(DISTINCT user_id) AS mau,        
        COUNT(order_id) FILTER (WHERE status != 'canceled') AS paid_orders,        
        ROUND(SUM(total_amount) FILTER (WHERE status != 'canceled'), 2) AS monthly_revenue
    FROM orders
    GROUP BY DATE_TRUNC('month', created_at)
),
monthly_analytics AS (
    SELECT 
        sales_month,
        mau,
        paid_orders,
        monthly_revenue,        
        ROUND(monthly_revenue / NULLIF(paid_orders, 0), 2) AS monthly_aov,     
        LAG(monthly_revenue, 1) OVER (ORDER BY sales_month) AS prev_month_revenue,        
        SUM(monthly_revenue) OVER (ORDER BY sales_month) AS cumulative_revenue,   
        ROUND(
            AVG(mau) OVER (
                ORDER BY sales_month 
                ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
            ), 0
        ) AS avg_mau_prev_quarter
    FROM monthly_raw
)
SELECT 
    sales_month,
    mau,
    paid_orders,
    monthly_revenue,
    monthly_aov,
    cumulative_revenue,    
    ROUND(
        ((monthly_revenue - prev_month_revenue) / NULLIF(prev_month_revenue, 0)) * 100, 2
    ) AS mom_revenue_growth_pct,    
    ROUND(
        ((mau - avg_mau_prev_quarter) / NULLIF(avg_mau_prev_quarter, 0)) * 100, 2
    ) AS mau_vs_prev_quarter_pct
FROM monthly_analytics
ORDER BY sales_month ASC;
