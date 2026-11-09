import plotly.express as px
import streamlit as st

from db import fetch_dataframe

# SQL, який також використовується на дашборді (app.py)
MONTHLY_REVENUE_SQL = """
    SELECT TO_CHAR(order_date, 'YYYY-MM') AS month,
           ROUND(SUM(order_total), 2) AS revenue
    FROM shop_order
    WHERE order_status = 'Delivered'
    GROUP BY month
    ORDER BY month ASC;
"""

CATEGORY_SALES_SQL = """
    SELECT c.category_name,
           SUM(ol.qty) AS total_items_sold,
           ROUND(SUM(ol.qty * ol.price), 2) AS total_revenue
    FROM order_line ol
    JOIN product_item pi ON ol.product_item_id = pi.id
    JOIN product p ON pi.product_id = p.id
    JOIN product_category c ON p.category_id = c.id
    JOIN shop_order so ON ol.order_id = so.id
    WHERE so.order_status <> 'Cancelled'
    GROUP BY c.category_name
    ORDER BY total_revenue DESC;
"""


def _report(query, chart=None, params=(), **layout):
    """Виконує запит і (опційно) будує графік: chart = (px-функція, kwargs).
    Повертає (DataFrame, Figure | None)."""
    df = fetch_dataframe(query, params)
    if chart is None:
        return df, None
    plot, kwargs = chart
    fig = plot(df, **kwargs)
    fig.update_layout(template="plotly_white", **layout)
    return df, fig


# --- 10 звітів: кожен повертає (df, fig); fig = None для чисто табличних ---

def get_monthly_revenue():
    return _report(MONTHLY_REVENUE_SQL, (px.line, dict(
        x="month", y="revenue", markers=True, title="Monthly Revenue (Delivered Orders)",
        labels={"month": "Month", "revenue": "Revenue ($)"})))


def get_top_selling_products():
    return _report("""
        SELECT p.name AS product_name, pi.SKU, SUM(ol.qty) AS total_sold
        FROM order_line ol
        JOIN product_item pi ON ol.product_item_id = pi.id
        JOIN product p ON pi.product_id = p.id
        JOIN shop_order so ON ol.order_id = so.id
        WHERE so.order_status <> 'Cancelled'
        GROUP BY p.name, pi.SKU
        ORDER BY total_sold DESC
        LIMIT 5;
    """, (px.bar, dict(
        x="total_sold", y="product_name", orientation="h", title="Top 5 Best-Selling Products",
        labels={"total_sold": "Units Sold", "product_name": "Product Name"},
        color="total_sold", color_continuous_scale="Viridis")),
        yaxis={"categoryorder": "total ascending"})


def get_top_spending_clients():
    return _report("""
        SELECT u.id AS user_id, u.email_address, ROUND(SUM(so.order_total), 2) AS total_spent
        FROM site_user u
        JOIN shop_order so ON u.id = so.user_id
        WHERE so.order_status = 'Delivered'
        GROUP BY u.id, u.email_address
        ORDER BY total_spent DESC
        LIMIT 5;
    """, (px.bar, dict(
        x="email_address", y="total_spent", title="Top 5 High-Value Customers",
        labels={"email_address": "Customer Email", "total_spent": "Total Spent ($)"},
        color="total_spent")))


def get_low_stock_products(threshold: int = 10):
    return _report("""
        SELECT p.name AS product_name, pi.SKU, pi.qty_in_stock
        FROM product_item pi
        JOIN product p ON pi.product_id = p.id
        WHERE pi.qty_in_stock < %s
        ORDER BY pi.qty_in_stock ASC;
    """, params=(threshold,))


def get_order_status_distribution():
    return _report("""
        SELECT order_status, COUNT(id) AS orders_count
        FROM shop_order
        GROUP BY order_status;
    """, (px.pie, dict(
        names="order_status", values="orders_count", title="Order Status Distribution", hole=0.4)))


def get_avg_order_value_by_city():
    return _report("""
        SELECT a.city, ROUND(AVG(so.order_total), 2) AS avg_order_value
        FROM shop_order so
        JOIN address a ON so.shipping_address_id = a.id
        WHERE so.order_status = 'Delivered'
        GROUP BY a.city
        ORDER BY avg_order_value DESC;
    """, (px.bar, dict(
        x="city", y="avg_order_value", title="Average Order Value by City (Delivered Orders)",
        labels={"city": "City", "avg_order_value": "Avg Order Value ($)"})))


def get_category_sales():
    return _report(CATEGORY_SALES_SQL, (px.bar, dict(
        x="category_name", y="total_revenue", title="Revenue Breakdown by Product Category",
        labels={"category_name": "Category", "total_revenue": "Total Revenue ($)"},
        color="total_items_sold")))


def get_product_configurations():
    return _report("""
        SELECT p.name AS product_name, pi.SKU, pi.price, v.name AS variation, vo.value AS option_value
        FROM product_item pi
        JOIN product p ON pi.product_id = p.id
        JOIN product_configuration pc ON pi.id = pc.product_item_id
        JOIN variation_option vo ON pc.variation_option_id = vo.id
        JOIN variation v ON vo.variation_id = v.id
        ORDER BY p.name, pi.SKU;
    """)


def get_inactive_users():
    return _report("""
        SELECT u.id AS user_id, u.email_address, u.phone_number
        FROM site_user u
        LEFT JOIN shop_order so ON u.id = so.user_id
        WHERE so.id IS NULL;
    """)


def get_order_summary_report():
    return _report("""
        SELECT so.id AS order_id, u.email_address, so.order_date, so.order_status,
               COUNT(ol.id) AS items_count, so.order_total
        FROM shop_order so
        LEFT JOIN site_user u ON so.user_id = u.id
        LEFT JOIN order_line ol ON so.id = ol.order_id
        GROUP BY so.id, u.email_address, so.order_date, so.order_status, so.order_total
        ORDER BY so.order_date DESC;
    """)


REPORTS = {
    "1. Monthly Revenue Dynamics": get_monthly_revenue,
    "2. Top 5 Best-Selling Items": get_top_selling_products,
    "3. Top Spending Customers": get_top_spending_clients,
    "4. Low Stock Inventory Alert": get_low_stock_products,
    "5. Order Status Distribution": get_order_status_distribution,
    "6. Average Order Value by City": get_avg_order_value_by_city,
    "7. Sales by Category": get_category_sales,
    "8. Product Variation Configurations": get_product_configurations,
    "9. Inactive Users (No Orders)": get_inactive_users,
    "10. Detailed Order Summaries": get_order_summary_report,
}


def render_reports_page():
    """Main rendering function for Streamlit Reports tab."""
    st.header("Analytics & Business Intelligence Reports")
    choice = st.selectbox("Select Analytical Report", list(REPORTS))
    st.divider()
    st.subheader(choice.split(". ", 1)[1])

    # Звіти з додатковим елементом керування / повідомленням
    if choice.startswith("4."):
        threshold = st.slider("Stock Threshold", min_value=1, max_value=50, value=10)
        df, fig = get_low_stock_products(threshold)
        st.warning(f"Found {len(df)} items with stock under {threshold} units.")
    else:
        df, fig = REPORTS[choice]()
        if choice.startswith("9."):
            st.info(f"Total inactive users: {len(df)}")

    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True)