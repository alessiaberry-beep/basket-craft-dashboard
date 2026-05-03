import streamlit as st
import snowflake.connector
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.title("Basket Craft Dashboard")


@st.cache_resource
def get_snowflake_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


@st.cache_data(ttl=600)
def get_dimension_table_counts():
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    # Get all dimension tables (tables starting with 'dim_')
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = CURRENT_SCHEMA()
        AND LOWER(table_name) LIKE 'dim_%'
    """)
    dim_tables = [row[0] for row in cursor.fetchall()]

    # Get row count for each dimension table
    counts = {}
    for table in dim_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]

    cursor.close()
    return counts


@st.cache_data(ttl=600)
def get_headline_metrics():
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    cursor.execute("""
        WITH monthly_metrics AS (
            SELECT
                DATE_TRUNC('month', order_date) AS month,
                SUM(total_amount) AS revenue,
                COUNT(DISTINCT order_id) AS orders,
                SUM(quantity) AS items_sold
            FROM fct_orders
            WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '2 months'
            GROUP BY DATE_TRUNC('month', order_date)
            ORDER BY month DESC
            LIMIT 2
        )
        SELECT
            month,
            revenue,
            orders,
            revenue / NULLIF(orders, 0) AS avg_order_value,
            items_sold
        FROM monthly_metrics
        ORDER BY month DESC
    """)

    rows = cursor.fetchall()
    cursor.close()

    if len(rows) >= 1:
        current = {
            "revenue": rows[0][1] or 0,
            "orders": rows[0][2] or 0,
            "aov": rows[0][3] or 0,
            "items": rows[0][4] or 0,
        }
    else:
        current = {"revenue": 0, "orders": 0, "aov": 0, "items": 0}

    if len(rows) >= 2:
        prior = {
            "revenue": rows[1][1] or 0,
            "orders": rows[1][2] or 0,
            "aov": rows[1][3] or 0,
            "items": rows[1][4] or 0,
        }
    else:
        prior = {"revenue": 0, "orders": 0, "aov": 0, "items": 0}

    return current, prior


@st.cache_data(ttl=600)
def get_revenue_trend(start_date: date, end_date: date):
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            DATE(order_date) AS order_day,
            SUM(total_amount) AS daily_revenue
        FROM fct_orders
        WHERE order_date >= %s AND order_date <= %s
        GROUP BY DATE(order_date)
        ORDER BY order_day
        """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    rows = cursor.fetchall()
    cursor.close()

    df = pd.DataFrame(rows, columns=["Date", "Revenue"])
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@st.cache_data(ttl=600)
def get_top_products(start_date: date, end_date: date, limit: int = 10):
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            p.product_name,
            SUM(o.total_amount) AS revenue
        FROM fct_orders o
        JOIN dim_products p ON o.product_id = p.product_id
        WHERE o.order_date >= %s AND o.order_date <= %s
        GROUP BY p.product_name
        ORDER BY revenue DESC
        LIMIT %s
        """,
        (start_date.isoformat(), end_date.isoformat(), limit),
    )

    rows = cursor.fetchall()
    cursor.close()

    df = pd.DataFrame(rows, columns=["Product", "Revenue"])
    return df


@st.cache_data(ttl=600)
def get_all_products():
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_id, product_name
        FROM dim_products
        ORDER BY product_name
    """)

    rows = cursor.fetchall()
    cursor.close()

    return {row[1]: row[0] for row in rows}


@st.cache_data(ttl=600)
def get_copurchased_products(product_id: int, limit: int = 10):
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        WITH orders_with_product AS (
            SELECT DISTINCT order_id
            FROM fct_orders
            WHERE product_id = %s
        )
        SELECT
            p.product_name,
            COUNT(DISTINCT o.order_id) AS co_purchase_count
        FROM fct_orders o
        JOIN orders_with_product owp ON o.order_id = owp.order_id
        JOIN dim_products p ON o.product_id = p.product_id
        WHERE o.product_id != %s
        GROUP BY p.product_name
        ORDER BY co_purchase_count DESC
        LIMIT %s
        """,
        (product_id, product_id, limit),
    )

    rows = cursor.fetchall()
    cursor.close()

    df = pd.DataFrame(rows, columns=["Product", "Orders Together"])
    return df


st.header("Headline Metrics")

try:
    current, prior = get_headline_metrics()

    def calc_delta(curr, prev):
        if prev == 0:
            return None
        return ((curr - prev) / prev) * 100

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        delta = calc_delta(current["revenue"], prior["revenue"])
        st.metric(
            label="Total Revenue",
            value=f"${current['revenue']:,.2f}",
            delta=f"{delta:+.1f}%" if delta is not None else None,
        )

    with col2:
        delta = calc_delta(current["orders"], prior["orders"])
        st.metric(
            label="Total Orders",
            value=f"{current['orders']:,}",
            delta=f"{delta:+.1f}%" if delta is not None else None,
        )

    with col3:
        delta = calc_delta(current["aov"], prior["aov"])
        st.metric(
            label="Avg Order Value",
            value=f"${current['aov']:,.2f}",
            delta=f"{delta:+.1f}%" if delta is not None else None,
        )

    with col4:
        delta = calc_delta(current["items"], prior["items"])
        st.metric(
            label="Total Items Sold",
            value=f"{current['items']:,}",
            delta=f"{delta:+.1f}%" if delta is not None else None,
        )

except Exception as e:
    st.error(f"Error loading headline metrics: {e}")

st.divider()

st.header("Revenue Trend")

default_end = date.today()
default_start = default_end - timedelta(days=90)

col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input("Start Date", value=default_start)
with col_end:
    end_date = st.date_input("End Date", value=default_end)

if start_date > end_date:
    st.error("Start date must be before end date.")
else:
    try:
        revenue_df = get_revenue_trend(start_date, end_date)
        if not revenue_df.empty:
            st.line_chart(revenue_df, x="Date", y="Revenue")
        else:
            st.info("No revenue data found for the selected date range.")
    except Exception as e:
        st.error(f"Error loading revenue trend: {e}")

    st.subheader("Top Products by Revenue")

    try:
        products_df = get_top_products(start_date, end_date)
        if not products_df.empty:
            st.bar_chart(products_df, x="Product", y="Revenue", horizontal=True)
        else:
            st.info("No product data found for the selected date range.")
    except Exception as e:
        st.error(f"Error loading top products: {e}")

st.divider()

st.header("Bundle Finder")

try:
    products = get_all_products()
    if products:
        selected_product = st.selectbox(
            "Select a product to find frequently bought together items:",
            options=list(products.keys()),
            index=None,
            placeholder="Choose a product...",
        )

        if selected_product:
            product_id = products[selected_product]
            copurchased_df = get_copurchased_products(product_id)

            if not copurchased_df.empty:
                st.write(f"Products most often purchased with **{selected_product}**:")
                st.dataframe(
                    copurchased_df,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No co-purchased products found.")
    else:
        st.info("No products found.")
except Exception as e:
    st.error(f"Error loading bundle finder: {e}")

st.divider()

st.header("Smoke Test: Dimension Table Row Counts")

try:
    counts = get_dimension_table_counts()
    if counts:
        for table, count in counts.items():
            st.metric(label=table, value=f"{count:,} rows")
    else:
        st.info("No dimension tables (dim_*) found in the current schema.")
except Exception as e:
    st.error(f"Connection error: {e}")
