from core.my_agent import MyVanna
from core.adapter import DBAdapter
from config.config import vn

# Connect to database using adapter
db_path = "db/ecommerce.db"
db_adapter = DBAdapter(f"sqlite:///{db_path}")

# Set the adapter for Vanna
vn.db_adapter = db_adapter

# Test connection
try:
    tables = db_adapter.list_tables()
    print(f"✅ Successfully connected to {db_path}")
    print(f"📋 Available tables: {tables}")
except Exception as e:
    print(f"❌ Failed to connect to database: {e}")
    exit(1)

# === 1. Training from DDL ===
print("\n=== Getting DDL statements ===")
try:
    df_ddl = db_adapter.run_sql("SELECT type, sql FROM sqlite_master WHERE sql IS NOT NULL")
    print("DDL statements found:", len(df_ddl))
    for ddl in df_ddl['sql'].to_list():
        vn.train(ddl=ddl)
except Exception as e:
    print(f"❌ Error getting DDL: {e}")

# === 2. Training questions with actual orders table ===
vn.train(question="Which city has the highest total sales in the last 6 months?",
         sql="""
WITH city_stats AS (
    SELECT orders.city AS location,
           'City' AS location_type,
           COUNT(*) AS order_count,
           SUM(orders.gross_amount_after_tax) AS total_order_value
    FROM orders
    WHERE DATE(substr(orders.date_created, 1, 10)) >= DATE('now', '-6 months')
    AND orders.city IS NOT NULL
    GROUP BY orders.city
)
SELECT location, order_count, total_order_value
FROM city_stats
ORDER BY total_order_value DESC
LIMIT 1;
""")

vn.train(question="How many orders were cancelled and what were the common reasons?",
         sql="""
SELECT orders.cancel_reason, COUNT(*) AS count
FROM orders
WHERE orders.order_status = 'cancelled'
GROUP BY orders.cancel_reason
ORDER BY count DESC;
""")

vn.train(question="What is the average gross amount per country?",
         sql="""
SELECT orders.country, AVG(orders.gross_amount_after_tax) AS avg_order_value
FROM orders
WHERE orders.country IS NOT NULL
GROUP BY orders.country
ORDER BY avg_order_value DESC;
""")

vn.train(question="What is the most used discount code?",
         sql="""
SELECT orders.discount_code, COUNT(*) AS usage_count
FROM orders
WHERE orders.discount_code IS NOT NULL
GROUP BY orders.discount_code
ORDER BY usage_count DESC
LIMIT 1;
""")

vn.train(question="What are the total orders per category?",
         sql="""
SELECT c.name AS category_name, COUNT(*) AS total_orders
FROM orders o
JOIN products p ON o.product_id = p.id
JOIN categories c ON p.category_id = c.id
GROUP BY c.name
ORDER BY total_orders DESC;
""")

vn.train(question="Show me all products with their categories",
         sql="""
SELECT p.name AS product_name, p.description, c.name AS category_name
FROM products p
JOIN categories c ON p.category_id = c.id
ORDER BY c.name, p.name;
""")

vn.train(question="Find orders with product details",
         sql="""
SELECT o.id AS order_id, o.gross_amount_after_tax, p.name AS product_name, c.name AS category_name
FROM orders o
JOIN products p ON o.product_id = p.id
JOIN categories c ON p.category_id = c.id
ORDER BY o.gross_amount_after_tax DESC;
""")

# === 3. Documentation to teach AI logic and avoid ambiguity ===
vn.train(documentation="""
-- Database stores e-commerce data with 3 main tables:
1. orders: includes data about transactions, customers, pricing, location, and status.
2. products: describes the product name, description, and category.
3. categories: product categories like electronics, clothing, etc.

-- SQL Best Practices (MANDATORY):
- ALWAYS use table names before column names: table_name.column_name
- Use table aliases for better readability: orders o, products p, categories c
- When joining tables, always specify table names: o.product_id = p.id
- In WHERE clauses, always prefix columns with table names: orders.status = 'active'
- In GROUP BY, always use table prefixes: GROUP BY orders.city
- In ORDER BY, always use table prefixes: ORDER BY orders.gross_amount_after_tax

-- Date Format Handling:
- All date columns (e.g., orders.date_created) are in TEXT format with `YYYY-MM-DD HH:MM:SS`.
- When filtering by time, extract the date using `substr(orders.date_created, 1, 10)` and compare with `DATE()`.

-- Table Relationships:
- orders.product_id → products.id
- products.category_id → categories.id

-- Interpretation of ambiguous terms:
- 'Significant' means a large number or value, usually defined by top-ranking or higher than average.
- 'Minor' means small number/value, often at the bottom or under a threshold (e.g. < 100 orders).
- 'Interesting' means unusual, surprising, or potentially insightful patterns in the data. These often require custom criteria (e.g., sudden spikes or anomalies).

-- Examples of CORRECT SQL patterns:
- SELECT orders.city, COUNT(*) FROM orders GROUP BY orders.city
- SELECT o.gross_amount_after_tax, p.name FROM orders o JOIN products p ON o.product_id = p.id
- SELECT c.name, COUNT(*) FROM orders o JOIN products p ON o.product_id = p.id JOIN categories c ON p.category_id = c.id GROUP BY c.name
""")

# === 4. Check loaded training data ===
print("\n=== Training data summary ===")
print("Training data in memory:", len(vn.training_data))
print("Training data content:", vn.training_data[:3] if vn.training_data else "Empty")

df = vn.get_training_data()
print("get_training_data result:", df)

vn.save_training_data()
print("✅ Training data saved successfully!")
