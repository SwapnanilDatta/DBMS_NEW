import pandas as pd
import os

def normalize_superstore_data(input_csv_path='Sample - Superstore.csv'):
    """
    Reads the Superstore CSV, normalizes its structure to 5NF,
    and saves the resulting tables as separate CSV files.

    Args:
        input_csv_path (str): The path to the input CSV file.
    """
    # --- 1. Load the Dataset ---
    try:
        df = pd.read_csv(input_csv_path, encoding='windows-1252')
        print(f"Successfully loaded '{input_csv_path}'.")
    except FileNotFoundError:
        print(f"Error: The file '{input_csv_path}' was not found.")
        return
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        return

    # Create an output directory
    output_dir = 'normalized_superstore_data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: '{output_dir}'")

    # --- 2. Decompose into Separate Tables (Normalization) ---

    # Table: Customers
    # Contains information unique to each customer.
    # PK: Customer ID
    # FIX: Ensure uniqueness on 'Customer ID'
    df_customers = df[['Customer ID', 'Customer Name', 'Segment']].drop_duplicates(subset=['Customer ID']).reset_index(drop=True)
    df_customers.rename(columns={'Customer ID': 'CustomerID', 'Customer Name': 'CustomerName'}, inplace=True)
    df_customers.to_csv(os.path.join(output_dir, 'customers.csv'), index=False)
    print("Created customers.csv")

    # Table: Locations
    # Contains geographical information based on postal code.
    # PK: Postal Code
    df_locations = df[['Postal Code', 'City', 'State', 'Region']].drop_duplicates(subset=['Postal Code']).reset_index(drop=True)
    df_locations.rename(columns={'Postal Code': 'PostalCode'}, inplace=True)
    df_locations.to_csv(os.path.join(output_dir, 'locations.csv'), index=False)
    print("Created locations.csv")

    # Table: Categories
    # Contains unique product categories.
    # PK: CategoryID (surrogate key)
    df_categories = pd.DataFrame(df['Category'].unique(), columns=['CategoryName'])
    df_categories['CategoryID'] = df_categories.index + 1  # Create a simple surrogate key
    df_categories = df_categories[['CategoryID', 'CategoryName']]
    df_categories.to_csv(os.path.join(output_dir, 'categories.csv'), index=False)
    print("Created categories.csv")

    # Table: SubCategories
    # Links sub-categories to their parent categories.
    # PK: SubCategoryID (surrogate key), FK: CategoryID
    df_sub_categories = df[['Category', 'Sub-Category']].drop_duplicates().reset_index(drop=True)
    df_sub_categories.rename(columns={'Category': 'CategoryName', 'Sub-Category': 'SubCategoryName'}, inplace=True)
    
    # Merge to get CategoryID
    df_sub_categories = pd.merge(df_sub_categories, df_categories, on='CategoryName')
    df_sub_categories['SubCategoryID'] = df_sub_categories.index + 1 # Surrogate key
    df_sub_categories = df_sub_categories[['SubCategoryID', 'SubCategoryName', 'CategoryID']]
    df_sub_categories.to_csv(os.path.join(output_dir, 'sub_categories.csv'), index=False)
    print("Created sub_categories.csv")

    # Table: Products
    # Contains information about each unique product.
    # PK: ProductID, FK: SubCategoryID
    df_products = df[['Product ID', 'Product Name', 'Sub-Category']].drop_duplicates(subset=['Product ID']).reset_index(drop=True)
    df_products.rename(columns={'Product ID': 'ProductID', 'Product Name': 'ProductName', 'Sub-Category': 'SubCategoryName'}, inplace=True)
    
    # Merge to get SubCategoryID
    df_products = pd.merge(df_products, df_sub_categories[['SubCategoryID', 'SubCategoryName']], on='SubCategoryName')
    df_products = df_products[['ProductID', 'ProductName', 'SubCategoryID']]
    df_products.to_csv(os.path.join(output_dir, 'products.csv'), index=False)
    print("Created products.csv")

    # Table: Orders
    # Contains information about each order transaction.
    # PK: OrderID, FKs: CustomerID, PostalCode
    df_orders = df[['Order ID', 'Order Date', 'Ship Date', 'Ship Mode', 'Customer ID', 'Postal Code']].drop_duplicates(subset=['Order ID']).reset_index(drop=True)
    df_orders.rename(columns={
        'Order ID': 'OrderID', 'Order Date': 'OrderDate', 'Ship Date': 'ShipDate',
        'Ship Mode': 'ShipMode', 'Customer ID': 'CustomerID', 'Postal Code': 'PostalCode'
    }, inplace=True)
    df_orders.to_csv(os.path.join(output_dir, 'orders.csv'), index=False)
    print("Created orders.csv")

    # Table: OrderDetails
    # This is the junction/linking table for orders and products.
    # PK: (OrderID, ProductID) (composite key)
    # FIX: Aggregate duplicate Order/Product pairs.
    df_order_details = df.groupby(['Order ID', 'Product ID']).agg({
        'Sales': 'sum',
        'Quantity': 'sum',
        'Discount': 'mean',
        'Profit': 'sum'
    }).reset_index()
    df_order_details.rename(columns={'Order ID': 'OrderID', 'Product ID': 'ProductID'}, inplace=True)
    df_order_details.to_csv(os.path.join(output_dir, 'order_details.csv'), index=False)
    print("Created order_details.csv")

    print(f"\nNormalization complete. All files are saved in the '{output_dir}' directory.")

if __name__ == '__main__':
    # Make sure 'Sample - Superstore.csv' is in the same directory as the script,
    # or provide the full path to the file.
    normalize_superstore_data('Sample - Superstore.csv')

