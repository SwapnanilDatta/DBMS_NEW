import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector
from mysql.connector import Error
import seaborn as sns
import matplotlib.pyplot as plt

# --- Page Configuration ---
st.set_page_config(
    page_title="Sales Analysis Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- Database Connection ---
db_config = {
    "host": st.secrets["database"]["host"],
    "port": st.secrets["database"]["port"],
    "user": st.secrets["database"]["user"],
    "password": st.secrets["database"]["password"],
    "database": st.secrets["database"]["database"],
}

@st.cache_resource
def init_connection():
    """Initializes a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(**db_config)
        st.success("✅ Database connection successful!")
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL database: {e}", icon="🔥")
        return None

# Get the database connection
conn = init_connection()

@st.cache_data(ttl=600) # Cache data for 10 minutes
def run_query(query):
    """Executes a query and returns the result as a Pandas DataFrame."""
    if conn:
        try:
            # Reconnect if connection is lost
            if not conn.is_connected():
                conn.reconnect()
            df = pd.read_sql(query, conn)
            return df
        except Exception as e:
            st.error(f"Failed to execute query: {e}", icon="⚠️")
            return pd.DataFrame() # Return empty DataFrame on error
    return pd.DataFrame()

# --- Functions for Data Modification ---
def execute_mod_query(query, params):
    """Executes a modification query (INSERT, DELETE)."""
    if not conn or not conn.is_connected():
        st.error("Database is not connected.")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
        # After modification, clear the cache to reflect changes
        st.cache_data.clear()
        return True
    except Error as e:
        st.error(f"Database error: {e}")
        conn.rollback()
        return False

# --- Main Application ---
st.title("📊 Sales Analysis Dashboard")
st.markdown("An interactive dashboard to analyze sales data directly from the database.")

# Stop execution if connection failed
if not conn or not conn.is_connected():
    st.warning("Database connection is not available. Please check the credentials and `ca.pem` file.")
    st.stop()


# --- Define Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Dashboard Overview",
    "📦 Product Analysis",
    "👥 Customer Analysis",
    "🌍 Geographical Insights",
    "🚚 Order & Shipping",
    "💾 Data Management"
])


# --- TAB 1: Dashboard Overview ---
with tab1:
    st.header("Dashboard Overview")

    # KPIs Query
    kpi_query = """
    SELECT
        SUM(od.Sales) AS TotalSales,
        SUM(od.Profit) AS TotalProfit,
        COUNT(DISTINCT o.OrderID) AS TotalOrders,
        AVG(od.Sales) AS AverageSale
    FROM orders o
    JOIN order_details od ON o.OrderID = od.OrderID;
    """
    kpi_data = run_query(kpi_query)

    if not kpi_data.empty and kpi_data['TotalSales'].iloc[0] is not None:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Sales", f"${kpi_data['TotalSales'].iloc[0]:,.2f}")
        col2.metric("Total Profit", f"${kpi_data['TotalProfit'].iloc[0]:,.2f}")
        col3.metric("Total Orders", f"{kpi_data['TotalOrders'].iloc[0]:,}")
        col4.metric("Average Sale Value", f"${kpi_data['AverageSale'].iloc[0]:,.2f}")
    else:
        st.info("No data available for KPIs. Please check if the database contains data.")
    st.markdown("---")

    # Time Series Chart
    sales_over_time_query = """
    SELECT
        o.OrderDate,
        SUM(od.Sales) as DailySales
    FROM orders o
    JOIN order_details od ON o.OrderID = od.OrderID
    GROUP BY o.OrderDate
    ORDER BY o.OrderDate;
    """
    sales_over_time = run_query(sales_over_time_query)

    if not sales_over_time.empty:
        sales_over_time['OrderDate'] = pd.to_datetime(sales_over_time['OrderDate'])
        fig = px.line(sales_over_time, x='OrderDate', y='DailySales', title='Sales Over Time',
                      labels={'OrderDate': 'Date', 'DailySales': 'Total Sales ($)'})
        st.plotly_chart(fig, use_container_width=True)


# --- TAB 2: Product Analysis ---
with tab2:
    st.header("Product & Category Performance")

    # Product Sales Query
    product_sales_query = """
    SELECT
        c.CategoryName,
        sc.SubCategoryName,
        p.ProductName,
        SUM(od.Sales) AS TotalSales,
        SUM(od.Quantity) AS TotalQuantity,
        SUM(od.Profit) AS TotalProfit
    FROM categories c
    JOIN sub_categories sc ON c.CategoryID = sc.CategoryID
    JOIN products p ON sc.SubCategoryID = p.SubCategoryID
    JOIN order_details od ON p.ProductID = od.ProductID
    GROUP BY c.CategoryName, sc.SubCategoryName, p.ProductName
    ORDER BY TotalSales DESC;
    """
    product_data = run_query(product_sales_query)

    if not product_data.empty:
        col1, col2 = st.columns(2)
        with col1:
            # Sales by Category
            sales_by_cat = product_data.groupby('CategoryName')['TotalSales'].sum().reset_index()
            fig_cat = px.pie(sales_by_cat, names='CategoryName', values='TotalSales',
                             title='Sales Distribution by Category', hole=0.4)
            st.plotly_chart(fig_cat, use_container_width=True)
        with col2:
            # Profit by Sub-Category
            profit_by_subcat = product_data.groupby('SubCategoryName')['TotalProfit'].sum().reset_index().sort_values(by='TotalProfit', ascending=False)
            fig_subcat = px.bar(profit_by_subcat, x='SubCategoryName', y='TotalProfit',
                                title='Profit by Sub-Category', labels={'SubCategoryName': 'Sub-Category', 'TotalProfit': 'Total Profit ($)'})
            st.plotly_chart(fig_subcat, use_container_width=True)

        st.markdown("---")
        st.markdown("### Sub-Category Profitability Analysis")
        st.info("This plot visualizes average profit margin vs. average discount for each sub-category, colored by total profit.")

        # --- SQL Query ---
        profitability_query = """
        SELECT
            sc.SubCategoryName AS sub_category,
            SUM(od.Profit) AS profit,
            (SUM(od.Profit) / SUM(od.Sales)) * 100 AS profit_margin,
            AVG(od.Discount) AS discount
        FROM
            order_details od
        JOIN
            products p ON od.ProductID = p.ProductID
        JOIN
            sub_categories sc ON p.SubCategoryID = sc.SubCategoryID
        GROUP BY
            sc.SubCategoryName
        ORDER BY
            profit DESC;
        """

        # --- Run query ---
        profitability_data = run_query(profitability_query)

        # --- Check & plot ---
        if not profitability_data.empty:
            st.dataframe(
                profitability_data.style.format({
                    'profit': '${:,.2f}',
                    'profit_margin': '{:.2f}%',
                    'discount': '{:.2%}'
                }),
                use_container_width=True
            )

            st.markdown("### 📊 Avg Profit Margin (%) vs. Avg Discount by Sub-Category")

            # --- Visualization ---
            fig, ax = plt.subplots(figsize=(14, 8))

            sns.scatterplot(
                x='discount',
                y='profit_margin',
                data=profitability_data,
                s=250,              # bubble size
                hue='profit',       # color by profit
                palette='RdBu',     # diverging palette
                ax=ax
            )

            # --- Red dashed quadrant lines ---
            ax.axhline(0, color='red', linestyle='--', linewidth=1.5)       # Profit margin = 0 line
            ax.axvline(0.20, color='red', linestyle='--', linewidth=1.5)    # 20% discount threshold

            # --- Labels for each sub-category ---
            for i in range(profitability_data.shape[0]):
                ax.text(
                    x=profitability_data['discount'][i] + 0.005,
                    y=profitability_data['profit_margin'][i],
                    s=profitability_data['sub_category'][i],
                    fontsize=9,
                    color='black'
                )

            # --- Titles & style ---
            ax.set_title('Avg Profit Margin (%) vs. Avg Discount by Sub-Category', fontsize=16)
            ax.set_xlabel('Average Discount Applied', fontsize=12)
            ax.set_ylabel('Average Profit Margin (%)', fontsize=12)
            sns.despine()
            st.pyplot(fig)

        else:
            st.warning("No data available for profitability analysis.")

        st.markdown("### Replenishable Products Table")
        st.info("This table shows the top-selling products by quantity, which may need replenishment soon.")
        replenish_table = product_data[['ProductName', 'CategoryName', 'TotalQuantity', 'TotalSales']].sort_values(by='TotalQuantity', ascending=False).head(20)
        st.dataframe(replenish_table, use_container_width=True)

# --- TAB 3: Customer Analysis ---
with tab3:
    st.header("Customer Insights")
    # Customer Data Query
    customer_query = """
    SELECT
        c.CustomerID,
        c.CustomerName,
        c.Segment,
        SUM(od.Sales) as TotalSales,
        COUNT(DISTINCT o.OrderID) as OrderCount
    FROM customers c
    JOIN orders o ON c.CustomerID = o.CustomerID
    JOIN order_details od ON o.OrderID = od.OrderID
    GROUP BY c.CustomerID, c.CustomerName, c.Segment
    ORDER BY TotalSales DESC;
    """
    customer_data = run_query(customer_query)

    if not customer_data.empty:
        # Sales by Segment
        sales_by_segment = customer_data.groupby('Segment')['TotalSales'].sum().reset_index()
        fig_segment = px.bar(sales_by_segment, x='Segment', y='TotalSales', title='Sales by Customer Segment', color='Segment')
        st.plotly_chart(fig_segment, use_container_width=True)

        st.markdown("### Customer Product Purchase History")
        # Customer Selection
        customer_list = customer_data['CustomerName'].unique()
        selected_customer = st.selectbox("Select a Customer to view their purchase history:", customer_list)

        if selected_customer:
            customer_id = customer_data[customer_data['CustomerName'] == selected_customer]['CustomerID'].iloc[0]
            # Query for selected customer's purchases
            purchase_history_query = f"""
            SELECT
                o.OrderDate,
                p.ProductName,
                sc.SubCategoryName,
                od.Quantity,
                od.Sales,
                od.Profit
            FROM order_details od
            JOIN orders o ON od.OrderID = o.OrderID
            JOIN products p ON od.ProductID = p.ProductID
            JOIN sub_categories sc ON p.SubCategoryID = sc.SubCategoryID
            WHERE o.CustomerID = '{customer_id}'
            ORDER BY o.OrderDate DESC;
            """
            purchase_history = run_query(purchase_history_query)
            st.dataframe(purchase_history, use_container_width=True)


# --- TAB 4: Geographical Insights ---
with tab4:
    st.header("Geographical Sales Analysis")
    geo_query = """
    SELECT
        l.Region,
        l.State,
        l.City,
        SUM(od.Sales) as TotalSales,
        SUM(od.Profit) as TotalProfit
    FROM locations l
    JOIN orders o ON l.PostalCode = o.PostalCode
    JOIN order_details od ON o.OrderID = od.OrderID
    GROUP BY l.Region, l.State, l.City
    ORDER BY TotalSales DESC;
    """
    geo_data = run_query(geo_query)

    if not geo_data.empty:
        col1, col2 = st.columns([1,2])
        with col1:
             # Sales by Region
            sales_by_region = geo_data.groupby('Region')['TotalSales'].sum().reset_index()
            fig_region = px.pie(sales_by_region, names='Region', values='TotalSales',
                                title='Sales by Region', hole=0.4)
            st.plotly_chart(fig_region, use_container_width=True)
        with col2:
            # Sales by State
            sales_by_state = geo_data.groupby('State')['TotalSales'].sum().reset_index().sort_values(by='TotalSales', ascending=False)
            fig_state = px.bar(sales_by_state.head(15), x='State', y='TotalSales', title='Top 15 States by Sales')
            st.plotly_chart(fig_state, use_container_width=True)


# --- TAB 5: Order & Shipping ---
with tab5:
    st.header("Order & Shipping Mode Analysis")

    shipping_query = """
    SELECT
        o.ShipMode,
        AVG(DATEDIFF(o.ShipDate, o.OrderDate)) as AvgShippingTime,
        SUM(od.Sales) as TotalSales,
        COUNT(DISTINCT o.OrderID) as OrderCount
    FROM orders o
    JOIN order_details od ON o.OrderID = od.OrderID
    GROUP BY o.ShipMode;
    """
    shipping_data = run_query(shipping_query)

    if not shipping_data.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig_ship_sales = px.bar(shipping_data, x='ShipMode', y='TotalSales',
                                   title='Total Sales by Ship Mode', color='ShipMode')
            st.plotly_chart(fig_ship_sales, use_container_width=True)
        with col2:
            fig_ship_time = px.bar(shipping_data, x='ShipMode', y='AvgShippingTime',
                                   title='Average Shipping Time (Days) by Ship Mode', color='ShipMode')
            st.plotly_chart(fig_ship_time, use_container_width=True)


# --- TAB 6: Data Management ---
with tab6:
    st.header("Data Management")

    # --- Add New Product ---
    with st.expander("➕ Add a New Product"):
        with st.form("new_product_form", clear_on_submit=True):
            product_id = st.text_input("Product ID (e.g., PROD-1001)")
            product_name = st.text_input("Product Name")

            sub_category_ids = run_query("SELECT SubCategoryID FROM sub_categories")
            if not sub_category_ids.empty:
                sub_category_id = st.selectbox("Sub-Category ID", options=sub_category_ids['SubCategoryID'].unique())
            else:
                sub_category_id = st.number_input("Sub-Category ID", min_value=1, step=1)

            submitted = st.form_submit_button("Add Product")
            if submitted:
                if not all([product_id, product_name, sub_category_id]):
                    st.warning("Please fill out all fields.")
                else:
                    query = "INSERT INTO products (ProductID, ProductName, SubCategoryID) VALUES (%s, %s, %s)"
                    params = (product_id, product_name, sub_category_id)
                    if execute_mod_query(query, params):
                        st.success(f"✅ Product '{product_name}' added successfully!")
                    else:
                        st.error("❌ Failed to add product. Please check if the ID already exists.")

    # --- View & Search Products ---
    with st.expander("🔍 View or Search Products"):
        st.markdown("You can search products by **Product ID** below.")
        search_term = st.text_input("Search Product ID (leave blank to show all)", key="search_product")

        if search_term:
            query = f"SELECT * FROM products WHERE ProductID LIKE '%{search_term}%'"
        else:
            query = "SELECT * FROM products"

        product_data = run_query(query)


        if not product_data.empty:
            st.dataframe(product_data, use_container_width=True)
        else:
            st.info("No matching products found.")

    # --- Remove Product ---
    with st.expander("🗑️ Remove a Product"):
        st.warning(
            "⚠️ Deleting a product will also delete all its associated records "
            "(like order details) **if cascading constraints are set in MySQL**.",
            icon="🔥"
        )

        with st.form("delete_product_form", clear_on_submit=True):
            product_id_to_delete = st.text_input("Enter the Product ID to delete")

            submitted = st.form_submit_button("Delete Product")
            if submitted:
                if not product_id_to_delete:
                    st.warning("Please enter a Product ID.")
                else:
                    query_delete = "DELETE FROM products WHERE ProductID = %s"
                    params = (product_id_to_delete,)

                    if execute_mod_query(query_delete, params):
                        st.success(f"✅ Product '{product_id_to_delete}' and all related data deleted successfully!")
                    else:
                        st.error(f"❌ Failed to delete product '{product_id_to_delete}'. It may not exist or has dependencies.")

# --- Sidebar Info ---
st.sidebar.info(
    "This dashboard connects directly to a MySQL database. "
    "Ensure your `ca.pem` file and credentials are configured correctly."
)
st.sidebar.markdown("---")
st.sidebar.header("About")
st.sidebar.write(
    "A sales analysis app created for a DBMS project, demonstrating "
    "live data visualization with Streamlit, Plotly, and MySQL."
)
