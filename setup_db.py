import sqlite3
import random
from datetime import datetime, timedelta

# Create and connect to SQLite database
conn = sqlite3.connect("ecommerce.db")
cursor = conn.cursor()

# Create all tables
cursor.executescript("""
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT,
    email TEXT,
    city TEXT,
    country TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    price REAL,
    stock_quantity INTEGER
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date TEXT,
    status TEXT,
    total_amount REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id INTEGER PRIMARY KEY,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price REAL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
""")

# Seed customers
cities = ["London", "New York", "Toronto", "Sydney", "Berlin"]
countries = ["UK", "USA", "Canada", "Australia", "Germany"]

for i in range(1, 51):
    city_idx = random.randint(0, 4)
    cursor.execute("""
        INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)
    """, (
        i,
        f"Customer {i}",
        f"customer{i}@email.com",
        cities[city_idx],
        countries[city_idx],
        (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
    ))

# Seed products
product_names = {
    "Electronics": ["Laptop", "Phone", "Tablet", "Headphones", "Camera"],
    "Clothing":    ["T-Shirt", "Jeans", "Jacket", "Shoes", "Hat"],
    "Books":       ["Python Guide", "AWS Handbook", "ML Book", "SQL Basics", "Cloud Computing"],
    "Home":        ["Lamp", "Chair", "Desk", "Rug", "Curtains"],
    "Sports":      ["Yoga Mat", "Dumbbells", "Running Shoes", "Water Bottle", "Jump Rope"]
}

product_id = 1
for category, names in product_names.items():
    for name in names:
        cursor.execute("""
            INSERT INTO products VALUES (?, ?, ?, ?, ?)
        """, (
            product_id,
            name,
            category,
            round(random.uniform(10, 1000), 2),
            random.randint(10, 200)
        ))
        product_id += 1

# Seed orders and order items
statuses = ["completed", "pending", "shipped", "cancelled"]
order_id = 1
item_id = 1

for i in range(1, 201):
    customer_id = random.randint(1, 50)
    order_date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 364))).strftime("%Y-%m-%d")
    status = random.choice(statuses)
    total = 0
    items = []

    for _ in range(random.randint(1, 4)):
        pid = random.randint(1, 25)
        quantity = random.randint(1, 5)
        cursor.execute("SELECT price FROM products WHERE product_id = ?", (pid,))
        price = cursor.fetchone()[0]
        subtotal = round(quantity * price, 2)
        total += subtotal
        items.append((item_id, order_id, pid, quantity, price))
        item_id += 1

    cursor.execute("""
        INSERT INTO orders VALUES (?, ?, ?, ?, ?)
    """, (order_id, customer_id, order_date, status, round(total, 2)))

    for item in items:
        cursor.execute("""
            INSERT INTO order_items VALUES (?, ?, ?, ?, ?)
        """, item)

    order_id += 1

conn.commit()
conn.close()
print("Database created successfully!")
print("Tables: customers (50), products (25), orders (200)")