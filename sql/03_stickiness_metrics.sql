WITH daily_activity AS (
    SELECT DISTINCT
        DATE(created_at) AS activity_date,
        user_id
    FROM orders
    WHERE status != 'canceled'
),
calendar_days AS (
    SELECT DISTINCT activity_date 
    FROM daily_activity
),
dau_mau_calculated AS (
    SELECT 
        c.activity_date,       
        (
            SELECT COUNT(DISTINCT d.user_id) 
            FROM daily_activity d 
            WHERE d.activity_date = c.activity_date
        ) AS dau,    
        (
            SELECT COUNT(DISTINCT m.user_id)
            FROM daily_activity m
            WHERE m.activity_date BETWEEN c.activity_date - INTERVAL '29 days' AND c.activity_date
        ) AS rolling_mau_30d
    FROM calendar_days c
)
SELECT 
    activity_date,
    dau,
    rolling_mau_30d,
    ROUND((dau::NUMERIC / NULLIF(rolling_mau_30d, 0)) * 100, 2) AS stickiness_ratio_pct
FROM dau_mau_calculated
<<<<<<< HEAD
WHERE activity_date >= '2017-01-01' 
ORDER BY activity_date DESC;
=======
WHERE activity_date >= '2017-01-01'  
ORDER BY activity_date DESC;
>>>>>>> ac64861 (docs: finalize project1 documentation and scripts)
