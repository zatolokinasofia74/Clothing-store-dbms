import os
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker("en_US")
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Volume settings (increase these for even more data)
# ---------------------------------------------------------------------------
NUM_USERS = 500
INACTIVE_USER_SHARE = 0.10   # users who never ordered (needed by the "no orders" query)
NUM_ORDERS = 5000
SKUS_PER_PRODUCT = 8         # out of 25 possible size/colour combinations
PAGE_SIZE = 1000

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "clothing_store")
DB_USER = os.getenv("DB_USER", "store_admin")
DB_PASS = os.getenv("DB_PASS", "admin_password")

conn = psycopg2.connect(
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
)
cur = conn.cursor()

NOW = datetime.now(timezone.utc)

try:
    print("Clearing existing data...")
    cur.execute("""
        TRUNCATE TABLE
            order_line, shop_order, user_payment_method, product_configuration,
            variation_option, variation, product_item, product,
            product_category, user_address, address, site_user
        RESTART IDENTITY CASCADE;
    """)

    # -----------------------------------------------------------------------
    # 1. Categories
    # -----------------------------------------------------------------------
    category_names = ["Men's Clothing", "Women's Clothing", "Outerwear",
                      "Activewear", "Accessories"]
    cat_ids = {}
    for name in category_names:
        cur.execute(
            "INSERT INTO product_category (category_name, parent_category_id) "
            "VALUES (%s, NULL) RETURNING id;",
            (name,),
        )
        cat_ids[name] = cur.fetchone()[0]

    # -----------------------------------------------------------------------
    # 2. Users (created_at spread over the last ~14 months)
    # -----------------------------------------------------------------------
    print(f"Generating {NUM_USERS} users...")
    users = []
    user_signup_days = []  # days ago each user registered
    for _ in range(NUM_USERS):
        signup_days = random.randint(5, 420)
        created_at = NOW - timedelta(days=signup_days, hours=random.randint(0, 23))
        users.append((fake.unique.email(), fake.phone_number()[:20],
                      "password_hash_xyz", created_at))
        user_signup_days.append(signup_days)

    user_ids = [
        r[0] for r in execute_values(
            cur,
            "INSERT INTO site_user (email_address, phone_number, password, created_at) "
            "VALUES %s RETURNING id;",
            users, page_size=PAGE_SIZE, fetch=True,
        )
    ]
    signup_by_user = dict(zip(user_ids, user_signup_days))

    # -----------------------------------------------------------------------
    # 3. Addresses (limited city pool so city-level stats are meaningful)
    # -----------------------------------------------------------------------
    cities = [
        ("New York", "New York"), ("Los Angeles", "California"),
        ("Chicago", "Illinois"), ("Houston", "Texas"),
        ("Phoenix", "Arizona"), ("Philadelphia", "Pennsylvania"),
        ("San Diego", "California"), ("Dallas", "Texas"),
        ("Seattle", "Washington"), ("Denver", "Colorado"),
        ("Boston", "Massachusetts"), ("Miami", "Florida"),
        ("Atlanta", "Georgia"), ("Portland", "Oregon"),
        ("Austin", "Texas"),
    ]
    num_addresses = int(NUM_USERS * 1.5)
    print(f"Generating {num_addresses} addresses...")
    addresses = []
    for _ in range(num_addresses):
        city, region = random.choice(cities)
        addresses.append((fake.street_address()[:20], city, region, fake.postcode()))

    address_ids = [
        r[0] for r in execute_values(
            cur,
            "INSERT INTO address (street_number, city, region, postal_code) "
            "VALUES %s RETURNING id;",
            addresses, page_size=PAGE_SIZE, fetch=True,
        )
    ]

    # -----------------------------------------------------------------------
    # 4. User <-> address (exactly one default per user)
    # -----------------------------------------------------------------------
    user_addr_rows = []
    addresses_of_user = {}  # uid -> (default_address_id, [all address ids])
    for uid in user_ids:
        chosen = random.sample(address_ids, random.randint(1, 3))
        addresses_of_user[uid] = (chosen[0], chosen)
        for i, aid in enumerate(chosen):
            user_addr_rows.append((uid, aid, i == 0))

    execute_values(
        cur,
        "INSERT INTO user_address (user_id, address_id, is_default) VALUES %s;",
        user_addr_rows, page_size=PAGE_SIZE,
    )

    # -----------------------------------------------------------------------
    # 5. Products
    # -----------------------------------------------------------------------
    catalog = [
        ("Men's Clothing", "Essential Crewneck Tee", "TSH", 24.99),
        ("Men's Clothing", "Slim-Fit Stretch Chinos", "CNS", 59.99),
        ("Men's Clothing", "Oxford Button-Down Shirt", "OXF", 49.99),
        ("Men's Clothing", "Classic Polo Shirt", "POL", 34.99),
        ("Men's Clothing", "Heavyweight Fleece Hoodie", "HOD", 69.99),
        ("Men's Clothing", "Tailored Wool Blazer", "BLZ", 189.99),
        ("Men's Clothing", "Relaxed Fit Cargo Pants", "CRG", 54.99),
        ("Men's Clothing", "Graphic Streetwear Tee", "GTS", 29.99),

        ("Women's Clothing", "Ribbed Knit Cardigan", "CDG", 44.99),
        ("Women's Clothing", "High-Waisted Denim Jeans", "JNS", 79.99),
        ("Women's Clothing", "Floral Chiffon Midi Dress", "DRS", 89.99),
        ("Women's Clothing", "Silk Wrap Blouse", "BLS", 64.99),
        ("Women's Clothing", "Pleated A-Line Skirt", "SKT", 39.99),
        ("Women's Clothing", "Linen Wide-Leg Trousers", "LNN", 59.99),
        ("Women's Clothing", "Cropped Denim Jacket", "CDJ", 74.99),
        ("Women's Clothing", "V-Neck Sleeveless Top", "VNK", 22.99),

        ("Outerwear", "Vintage Leather Biker Jacket", "LBJ", 249.99),
        ("Outerwear", "Waterproof Parka Coat", "PRK", 179.99),
        ("Outerwear", "Down-Filled Puffer Jacket", "PFJ", 159.99),
        ("Outerwear", "Classic Double-Breasted Trench", "TRN", 199.99),
        ("Outerwear", "Wool Blend Overcoat", "OVC", 219.99),
        ("Outerwear", "Windproof Softshell Jacket", "SSJ", 99.99),
        ("Outerwear", "Denim Sherpa Trucker Jacket", "STJ", 119.99),
        ("Outerwear", "Lightweight Bomber Jacket", "BMR", 84.99),

        ("Activewear", "Seamless Running Leggings", "LGG", 48.99),
        ("Activewear", "Moisture-Wicking Sports Bra", "SBR", 32.99),
        ("Activewear", "Performance Tech Shorts", "PTS", 36.99),
        ("Activewear", "Thermal Compression Shirt", "TCS", 42.99),
        ("Activewear", "Zip-Up Tracksuit Top", "TST", 64.99),
        ("Activewear", "Breathable Jogger Pants", "JGR", 49.99),
        ("Activewear", "Athletic Training Tank", "ATT", 26.99),
        ("Activewear", "Insulated Running Vest", "IRV", 58.99),

        ("Accessories", "Genuine Leather Belt", "BLT", 29.99),
        ("Accessories", "Merino Beanie Hat", "BNI", 19.99),
        ("Accessories", "Canvas Travel Backpack", "BPK", 69.99),
        ("Accessories", "Polarized Sunglasses", "SNG", 45.99),
        ("Accessories", "Woven Wool Scarf", "SCF", 27.99),
        ("Accessories", "Leather Crossbody Bag", "BAG", 89.99),
        ("Accessories", "Minimalist Wrist Watch", "WTC", 129.99),
        ("Accessories", "Cotton Sport Caps", "CAP", 18.99),
    ]

    product_rows = [
        (cat_ids[cat], name, None) for cat, name, _, _ in catalog
    ]
    product_ids = [
        r[0] for r in execute_values(
            cur,
            "INSERT INTO product (category_id, name, description) VALUES %s RETURNING id;",
            product_rows, fetch=True,
        )
    ]

    # -----------------------------------------------------------------------
    # 6. Variations and options (Size / Color per category)
    # -----------------------------------------------------------------------
    option_values = {
        "Size": ["XS", "S", "M", "L", "XL"],
        "Color": ["BLK", "WHT", "NVY", "RED", "GRN"],
    }

    variation_rows = [(cid, vname) for cid in cat_ids.values() for vname in option_values]
    execute_values(
        cur, "INSERT INTO variation (category_id, name) VALUES %s;", variation_rows
    )
    cur.execute("SELECT id, category_id, name FROM variation;")
    variation_map = {(cid, name): vid for vid, cid, name in cur.fetchall()}

    option_rows = [
        (vid, val)
        for (cid, name), vid in variation_map.items()
        for val in option_values[name]
    ]
    execute_values(
        cur, "INSERT INTO variation_option (variation_id, value) VALUES %s;", option_rows
    )
    cur.execute("""
        SELECT vo.id, v.category_id, v.name, vo.value, vo.variation_id
        FROM variation_option vo
        JOIN variation v ON vo.variation_id = v.id;
    """)
    option_map = {
        (cid, name, val): (opt_id, var_id)
        for opt_id, cid, name, val, var_id in cur.fetchall()
    }

    # -----------------------------------------------------------------------
    # 7. Product items (SKUs) with varied stock levels
    # -----------------------------------------------------------------------
    def random_stock():
        return random.randint(10, 200)     # healthy stock

    all_pairs = [(s, c) for s in option_values["Size"] for c in option_values["Color"]]

    item_rows = []
    sku_meta = {}  # sku -> (category_id, size, color)
    for pid, (cat, p_name, code, base_price) in zip(product_ids, catalog):
        cid = cat_ids[cat]
        for size, color in random.sample(all_pairs, SKUS_PER_PRODUCT):
            sku = f"{code}-{color}-{size}"
            price = max(0.0, round(base_price + random.choice([-2.0, 0.0, 3.0]), 2))
            is_active = random.random() > 0.03   # a few discontinued SKUs
            item_rows.append((pid, sku, price, random_stock(), is_active))
            sku_meta[sku] = (cid, size, color)

    # Pick 20 active SKUs as low-stock alerts with a clean staircase of values
    # (0,0,1,1,2,2,...,9,9) -> good for the "Warehouse Inventory Alerts" chart
    # and covers all three stock labels in the stock-status query.
    low_idx = random.sample([i for i, r in enumerate(item_rows)], 20)
    for step, idx in enumerate(low_idx):
        pid, sku, price, _, _ = item_rows[idx]
        item_rows[idx] = (pid, sku, price, step // 2, True)

    inserted_items = execute_values(
        cur,
        "INSERT INTO product_item (product_id, SKU, price, qty_in_stock, is_active) "
        "VALUES %s RETURNING id, SKU;",
        item_rows, page_size=PAGE_SIZE, fetch=True,
    )

    configurations = []
    for item_id, sku in inserted_items:
        cid, size, color = sku_meta[sku]
        for vname, val in (("Size", size), ("Color", color)):
            opt_id, var_id = option_map[(cid, vname, val)]
            configurations.append((item_id, opt_id, var_id))

    execute_values(
        cur,
        "INSERT INTO product_configuration "
        "(product_item_id, variation_option_id, variation_id) VALUES %s;",
        configurations, page_size=PAGE_SIZE,
    )

    # -----------------------------------------------------------------------
    # 8. Payment methods (one default per user)
    # -----------------------------------------------------------------------
    payment_rows = []
    for uid in user_ids:
        providers = random.sample(["Visa", "Mastercard", "PayPal", "Apple Pay"],
                                  random.randint(1, 2))
        for idx, provider in enumerate(providers):
            payment_rows.append((uid, provider, idx == 0))

    execute_values(
        cur,
        "INSERT INTO user_payment_method (user_id, provider, is_default) VALUES %s;",
        payment_rows, page_size=PAGE_SIZE,
    )

    # -----------------------------------------------------------------------
    # 9. Orders and order lines
    # -----------------------------------------------------------------------
    cur.execute("""
        SELECT pi.id, pi.price, pi.SKU, p.name
        FROM product_item pi
        JOIN product p ON pi.product_id = p.id;
    """)
    available_items = cur.fetchall()
    # Heavy-tailed popularity so "top products" has a clear ranking
    item_weights = [random.paretovariate(1.5) for _ in available_items]

    # Some users never order
    shuffled = user_ids[:]
    random.shuffle(shuffled)
    n_inactive = int(NUM_USERS * INACTIVE_USER_SHARE)
    buyers = shuffled[n_inactive:]
    # Some buyers are far more loyal than others
    buyer_weights = [random.paretovariate(2.0) for _ in buyers]

    def pick_status(age_days):
        if age_days <= 2:
            return random.choices(
                ["Pending", "Processing", "Cancelled"], [45, 45, 10])[0]
        if age_days <= 7:
            return random.choices(
                ["Processing", "Shipped", "Delivered", "Cancelled"],
                [15, 35, 40, 10])[0]
        return random.choices(["Delivered", "Cancelled"], [88, 12])[0]

    print(f"Generating {NUM_ORDERS} orders...")
    order_rows = []
    line_rows = []
    for order_id in range(1, NUM_ORDERS + 1):
        uid = random.choices(buyers, buyer_weights)[0]

        # More orders in recent months (business growth), never before signup
        age = 365 * random.random() ** 1.4
        if age > signup_by_user[uid]:
            age = random.uniform(0, signup_by_user[uid])
        order_date = NOW - timedelta(days=age, minutes=random.randint(0, 59))
        status = pick_status(age)

        default_addr, all_addrs = addresses_of_user[uid]
        ship_addr = default_addr if random.random() < 0.7 else random.choice(all_addrs)

        # Distinct items for this order, weighted by popularity
        wanted = random.choices([1, 2, 3, 4, 5], [35, 30, 20, 10, 5])[0]
        chosen = {}
        while len(chosen) < wanted:
            item = random.choices(available_items, item_weights)[0]
            chosen[item[0]] = item

        total = Decimal("0.00")
        for item_id, item_price, item_sku, item_name in chosen.values():
            qty = random.choices([1, 2, 3], [65, 25, 10])[0]
            price = Decimal(item_price)
            total += qty * price
            line_rows.append((order_id, item_id, item_name, item_sku, qty, price))

        order_rows.append((order_id, uid, ship_addr, order_date, total, status))

    execute_values(
        cur,
        "INSERT INTO shop_order "
        "(id, user_id, shipping_address_id, order_date, order_total, order_status) "
        "VALUES %s;",
        order_rows, page_size=PAGE_SIZE,
    )
    # Keep the SERIAL sequence in sync after inserting explicit ids
    cur.execute(
        "SELECT setval(pg_get_serial_sequence('shop_order', 'id'), "
        "(SELECT MAX(id) FROM shop_order));"
    )

    execute_values(
        cur,
        "INSERT INTO order_line "
        "(order_id, product_item_id, product_name, SKU, qty, price) VALUES %s;",
        line_rows, page_size=PAGE_SIZE,
    )

    conn.commit()
    print("Database successfully populated!")
    print(
        f"Summary: {len(user_ids)} users ({n_inactive} without orders), "
        f"{len(address_ids)} addresses, {len(product_ids)} products, "
        f"{len(item_rows)} SKUs, {NUM_ORDERS} orders, {len(line_rows)} order lines."
    )

except Exception as err:
    conn.rollback()
    print(f"Database error: {err}")
    raise
finally:
    cur.close()
    conn.close()