-- ==========================================
-- PRESYOPH DATABASE SCHEMA
-- ==========================================

CREATE DATABASE IF NOT EXISTS presyoph_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE presyoph_db;


-- ==========================================
-- AREAS TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS areas (
    area_id INT AUTO_INCREMENT PRIMARY KEY,
    area_name VARCHAR(255) NOT NULL UNIQUE
);


-- ==========================================
-- CATEGORIES TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL UNIQUE
);

-- ==========================================
-- CPI TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS cpi (
    cpi_id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    area_id INT NOT NULL,
    category_id INT NOT NULL,
    value DECIMAL(15,6) NOT NULL,
    base_year INT NOT NULL,

    CONSTRAINT fk_cpi_area
        FOREIGN KEY (area_id)
        REFERENCES areas(area_id),

    CONSTRAINT fk_cpi_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id),

    CONSTRAINT uq_cpi_observation
        UNIQUE (date, area_id, category_id)
);

-- ==========================================
-- INFLATION TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS inflation (
    inflation_id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    area_id INT NOT NULL,
    category_id INT NOT NULL,
    value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50) NOT NULL,

    CONSTRAINT fk_inflation_area
        FOREIGN KEY (area_id)
        REFERENCES areas(area_id),

    CONSTRAINT fk_inflation_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id),

    CONSTRAINT uq_inflation_observation
        UNIQUE (date, area_id, category_id)
);

-- ==========================================
-- PURCHASING POWER TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS purchasing_power (
    purchasing_power_id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    area_id INT NOT NULL,
    value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    base_year INT NOT NULL,

    CONSTRAINT fk_purchasing_power_area
        FOREIGN KEY (area_id)
        REFERENCES areas(area_id),

    CONSTRAINT uq_purchasing_power_observation
        UNIQUE (date, area_id)
);

-- ==========================================
-- FIES TABLE
-- ==========================================

CREATE TABLE IF NOT EXISTS fies (
    fies_id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL,
    area VARCHAR(255) NOT NULL,
    income_group VARCHAR(100) NOT NULL,
    indicator VARCHAR(100) NOT NULL,
    value DECIMAL(15,2) NOT NULL,
    unit VARCHAR(50) NOT NULL,

    CONSTRAINT uq_fies_observation
        UNIQUE (year, area, income_group, indicator)
);