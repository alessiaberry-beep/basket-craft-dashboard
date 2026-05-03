# Basket Craft Dashboard

**Live App:** https://alessiaberry-beep-basket-craft-dashboard-app-ksqgkz.streamlit.app

A Streamlit dashboard for Basket Craft analytics, connected to Snowflake.

## Features

- **Headline Metrics** - Total revenue, orders, AOV, and items sold with month-over-month comparison
- **Revenue Trend** - Daily revenue line chart with date range filter
- **Top Products** - Bar chart showing top products by revenue
- **Bundle Finder** - Discover products frequently purchased together

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Snowflake credentials:
   ```
   SNOWFLAKE_ACCOUNT=your_account
   SNOWFLAKE_USER=your_user
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_ROLE=your_role
   SNOWFLAKE_WAREHOUSE=your_warehouse
   SNOWFLAKE_DATABASE=your_database
   SNOWFLAKE_SCHEMA=your_schema
   ```

4. Run the app:
   ```bash
   streamlit run app.py
   ```
