SELECT DATE_TRUNC('month', order_date)::DATE AS month,
       COUNT(*) AS orders_count,
       ROUND(SUM(order_total), 2) AS revenue,
       ROUND(AVG(order_total), 2) AS avg_order_value
FROM shop_order
WHERE order_status = 'Delivered'
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month DESC;

SELECT p.name AS product_name,
       pi.SKU,
       SUM(ol.qty) AS total_sold,
       ROUND(SUM(ol.qty * ol.price), 2) AS total_revenue,
       COUNT(DISTINCT ol.order_id) AS orders_count
FROM order_line ol
JOIN product_item pi ON ol.product_item_id = pi.id
JOIN product p ON pi.product_id = p.id
JOIN shop_order so ON ol.order_id = so.id
WHERE so.order_status <> 'Cancelled'
GROUP BY p.id, p.name, pi.id, pi.SKU
ORDER BY total_sold DESC, total_revenue DESC
LIMIT 5;

SELECT u.id AS user_id,
       u.email_address,
       COUNT(so.id) AS orders_count,
       ROUND(SUM(so.order_total), 2) AS total_spent,
       ROUND(AVG(so.order_total), 2) AS avg_order_value
FROM site_user u
JOIN shop_order so ON u.id = so.user_id
WHERE so.order_status = 'Delivered'
GROUP BY u.id, u.email_address
ORDER BY total_spent DESC
LIMIT 5;


SELECT p.name AS product_name,
       c.category_name,
       pi.SKU,
       pi.price,
       pi.qty_in_stock,
       CASE
           WHEN pi.qty_in_stock = 0 THEN 'Out of stock'
           WHEN pi.qty_in_stock < 5 THEN 'Critically low stock'
           ELSE 'Restocking required'
       END AS stock_status
FROM product_item pi
JOIN product p ON pi.product_id = p.id
JOIN product_category c ON p.category_id = c.id
WHERE pi.qty_in_stock < 10
  AND pi.is_active = TRUE
  AND p.is_active = TRUE
ORDER BY pi.qty_in_stock ASC, p.name;

SELECT order_status,
       COUNT(*) AS orders_count,
       ROUND(SUM(order_total), 2) AS total_amount,
       ROUND(AVG(order_total), 2) AS avg_order_value
FROM shop_order
GROUP BY order_status
ORDER BY orders_count DESC;

SELECT a.city,
       COUNT(so.id) AS orders_count,
       ROUND(AVG(so.order_total), 2) AS avg_order_value,
       ROUND(SUM(so.order_total), 2) AS total_order_value
FROM shop_order so
JOIN address a ON so.shipping_address_id = a.id
WHERE so.order_status = 'Delivered'
GROUP BY a.city
ORDER BY avg_order_value DESC;

SELECT c.category_name,
       SUM(ol.qty) AS total_items_sold,
       COUNT(DISTINCT ol.order_id) AS orders_count,
       ROUND(SUM(ol.qty * ol.price), 2) AS total_revenue,
       ROUND(
           SUM(ol.qty * ol.price) / NULLIF(SUM(ol.qty), 0), 2
       ) AS avg_item_price
FROM order_line ol
JOIN product_item pi ON ol.product_item_id = pi.id
JOIN product p ON pi.product_id = p.id
JOIN product_category c ON p.category_id = c.id
JOIN shop_order so ON ol.order_id = so.id
WHERE so.order_status <> 'Cancelled'
GROUP BY c.id, c.category_name
ORDER BY total_revenue DESC;


SELECT c.category_name,
       p.name AS product_name,
       pi.SKU,
       pi.price,
       pi.qty_in_stock,
       v.name AS variation_name,
       vo.value AS option_value
FROM product_item pi
JOIN product p ON pi.product_id = p.id
JOIN product_category c ON p.category_id = c.id
JOIN product_configuration pc ON pi.id = pc.product_item_id
JOIN variation_option vo
    ON pc.variation_option_id = vo.id
   AND pc.variation_id = vo.variation_id
JOIN variation v ON pc.variation_id = v.id
WHERE pi.is_active = TRUE
  AND p.is_active = TRUE
ORDER BY c.category_name, p.name, pi.SKU, v.name;


SELECT u.id AS user_id,
       u.email_address,
       u.phone_number,
       u.created_at,
       CURRENT_DATE - u.created_at::DATE AS days_since_registration
FROM site_user u
WHERE NOT EXISTS (
    SELECT 1
    FROM shop_order so
    WHERE so.user_id = u.id
)
ORDER BY u.created_at DESC;

SELECT so.id AS order_id,
       u.email_address,
       so.order_date,
       so.order_status,
       COUNT(ol.id) AS order_lines_count,
       COALESCE(SUM(ol.qty), 0) AS total_items_count,
       so.order_total
FROM shop_order so
LEFT JOIN site_user u ON so.user_id = u.id
LEFT JOIN order_line ol ON so.id = ol.order_id
GROUP BY so.id, u.email_address, so.order_date,
         so.order_status, so.order_total
ORDER BY so.order_date DESC;