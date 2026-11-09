
-- 1. ОЧИЩЕННЯ ТАБЛИЦЬ ДЛЯ ПОВТОРНОГО ЗАПУСКУ
DROP TABLE IF EXISTS test_init CASCADE;
DROP TABLE IF EXISTS order_line CASCADE;
DROP TABLE IF EXISTS shop_order CASCADE;
DROP TABLE IF EXISTS user_payment_method CASCADE;
DROP TABLE IF EXISTS product_configuration CASCADE;
DROP TABLE IF EXISTS variation_option CASCADE;
DROP TABLE IF EXISTS variation CASCADE;
DROP TABLE IF EXISTS product_item CASCADE;
DROP TABLE IF EXISTS product CASCADE;
DROP TABLE IF EXISTS product_category CASCADE;
DROP TABLE IF EXISTS user_address CASCADE;
DROP TABLE IF EXISTS address CASCADE;
DROP TABLE IF EXISTS site_user CASCADE;


-- =============================================================================
-- 2. КОРИСТУВАЧІ
-- =============================================================================

CREATE TABLE site_user (
    id SERIAL PRIMARY KEY,
    email_address VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(20) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =============================================================================
-- 3. АДРЕСИ
-- =============================================================================

CREATE TABLE address (
    id SERIAL PRIMARY KEY,
    street_number VARCHAR(20) NOT NULL,
    city VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL
);


-- =============================================================================
-- 4. ЗВ'ЯЗОК КОРИСТУВАЧІВ ТА АДРЕС
-- =============================================================================

CREATE TABLE user_address (
    user_id INT NOT NULL REFERENCES site_user(id) ON DELETE CASCADE,
    address_id INT NOT NULL REFERENCES address(id) ON DELETE CASCADE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, address_id)
);

-- Один користувач може мати лише одну адресу за замовчуванням.

CREATE UNIQUE INDEX uq_user_default_address
ON user_address(user_id)
WHERE is_default = TRUE;


-- =============================================================================
-- 5. КАТЕГОРІЇ ТОВАРІВ
-- =============================================================================

CREATE TABLE product_category (
    id SERIAL PRIMARY KEY,
    parent_category_id INT REFERENCES product_category(id) ON DELETE SET NULL,
    category_name VARCHAR(100) NOT NULL UNIQUE
);


-- =============================================================================
-- 6. ТОВАРИ
-- =============================================================================

CREATE TABLE product (
    id SERIAL PRIMARY KEY,
    category_id INT NOT NULL REFERENCES product_category(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);


-- =============================================================================
-- 7. ВАРІАНТИ ТОВАРІВ (SKU)
-- =============================================================================

CREATE TABLE product_item (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES product(id) ON DELETE RESTRICT,
    SKU VARCHAR(50) NOT NULL UNIQUE,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    qty_in_stock INT NOT NULL DEFAULT 0 CHECK (qty_in_stock >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);


-- =============================================================================
-- 8. ХАРАКТЕРИСТИКИ ТОВАРІВ
-- =============================================================================

CREATE TABLE variation (
    id SERIAL PRIMARY KEY,
    category_id INT NOT NULL REFERENCES product_category(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    UNIQUE (category_id, name)
);


-- =============================================================================
-- 9. ЗНАЧЕННЯ ХАРАКТЕРИСТИК
-- =============================================================================

CREATE TABLE variation_option (
    id SERIAL PRIMARY KEY,
    variation_id INT NOT NULL REFERENCES variation(id) ON DELETE CASCADE,
    value VARCHAR(100) NOT NULL,
    UNIQUE (variation_id, value),
    UNIQUE (id, variation_id)
);


-- =============================================================================
-- 10. КОНФІГУРАЦІЯ ВАРІАНТІВ ТОВАРІВ
-- =============================================================================

CREATE TABLE product_configuration (
    product_item_id INT NOT NULL REFERENCES product_item(id) ON DELETE CASCADE,
    variation_option_id INT NOT NULL,
    variation_id INT NOT NULL,
    PRIMARY KEY (product_item_id, variation_id),

    FOREIGN KEY (variation_option_id, variation_id)
        REFERENCES variation_option(id, variation_id)
        ON DELETE CASCADE
);


-- =============================================================================
-- 11. ЗАМОВЛЕННЯ
-- =============================================================================

CREATE TABLE shop_order (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES site_user(id) ON DELETE SET NULL,
    shipping_address_id INT REFERENCES address(id) ON DELETE SET NULL,
    order_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    order_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (order_total >= 0),
    order_status VARCHAR(30) NOT NULL DEFAULT 'Pending',

    CHECK (order_status IN (
        'Pending',
        'Processing',
        'Shipped',
        'Delivered',
        'Cancelled'
    ))
);


-- =============================================================================
-- 12. ПОЗИЦІЇ ЗАМОВЛЕНЬ
-- =============================================================================

CREATE TABLE order_line (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES shop_order(id) ON DELETE CASCADE,
    product_item_id INT REFERENCES product_item(id) ON DELETE SET NULL,
    product_name VARCHAR(255) NOT NULL,
    SKU VARCHAR(50) NOT NULL,
    qty INT NOT NULL CHECK (qty > 0),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0)
);


-- =============================================================================
-- 13. СПОСОБИ ОПЛАТИ КОРИСТУВАЧІВ
-- =============================================================================

CREATE TABLE user_payment_method (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES site_user(id) ON DELETE CASCADE,
    provider VARCHAR(100) NOT NULL,
    account_number VARCHAR(255),
    is_default BOOLEAN NOT NULL DEFAULT FALSE
);

-- Один користувач може мати лише один спосіб оплати за замовчуванням.

CREATE UNIQUE INDEX uq_user_default_payment
ON user_payment_method(user_id)
WHERE is_default = TRUE;


-- =============================================================================
-- 14. ІНДЕКСИ ДЛЯ ОПТИМІЗАЦІЇ
-- =============================================================================

-- Товари та категорії

CREATE INDEX idx_product_category
ON product(category_id);

CREATE INDEX idx_product_name
ON product(name);

CREATE INDEX idx_product_item_product
ON product_item(product_id);

-- Характеристики

CREATE INDEX idx_variation_category
ON variation(category_id);

CREATE INDEX idx_variation_option_variation
ON variation_option(variation_id);

CREATE INDEX idx_product_configuration_option
ON product_configuration(variation_option_id);

-- Замовлення

CREATE INDEX idx_shop_order_user
ON shop_order(user_id);

CREATE INDEX idx_shop_order_date
ON shop_order(order_date);

CREATE INDEX idx_shop_order_status
ON shop_order(order_status);

CREATE INDEX idx_order_line_order
ON order_line(order_id);

CREATE INDEX idx_order_line_item
ON order_line(product_item_id);

-- Адреси та способи оплати

CREATE INDEX idx_user_address_address
ON user_address(address_id);

CREATE INDEX idx_user_payment_user
ON user_payment_method(user_id);

