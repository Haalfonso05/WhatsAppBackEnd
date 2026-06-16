-- =============================================================
-- whatsapp_commerce  –  Supabase / PostgreSQL schema
-- Ejecutar en: Supabase Dashboard > SQL Editor
-- =============================================================

-- 1. Crear el schema
CREATE SCHEMA IF NOT EXISTS whatsapp_commerce;

-- 2. Tablas sin dependencias externas primero
-- -------------------------------------------------------------

CREATE TABLE whatsapp_commerce.payment_method (
    id_payment_method SERIAL      PRIMARY KEY,
    name              VARCHAR(20) NOT NULL
);

CREATE TABLE whatsapp_commerce.product_type (
    id_product_type SERIAL      PRIMARY KEY,
    name            VARCHAR(20) NOT NULL
);

CREATE TABLE whatsapp_commerce.customer (
    document     VARCHAR(10) PRIMARY KEY,
    name_1       VARCHAR(15) NOT NULL,
    name_2       VARCHAR(15),
    last_name_1  VARCHAR(15) NOT NULL,
    last_name_2  VARCHAR(15),
    address      TEXT,
    phone_number VARCHAR(15) NOT NULL
);

CREATE TABLE whatsapp_commerce.employe (
    id_card            SERIAL      PRIMARY KEY,
    name               VARCHAR(90),
    status             VARCHAR(1),
    supervisor_id      INTEGER     REFERENCES whatsapp_commerce.employe(id_card),
    type               VARCHAR(15) NOT NULL,
    target_day         NUMERIC(10,2),
    functions          TEXT,
    daily_rate         NUMERIC(12,2),
    number_of_sessions INTEGER,
    day_worked         VARCHAR(50),
    payment_day        NUMERIC(2)
);

CREATE TABLE whatsapp_commerce.courier (
    id_courier INTEGER     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(90) NOT NULL,
    id_card    VARCHAR(20) NOT NULL
);

-- 3. Tablas con dependencias
-- -------------------------------------------------------------

CREATE TABLE whatsapp_commerce.product (
    id_product      SERIAL        PRIMARY KEY,
    name            VARCHAR(100)  NOT NULL,
    reference_price NUMERIC(12,2) NOT NULL,
    current_stock   NUMERIC(10,2) DEFAULT 0,
    available       VARCHAR(1)    NOT NULL DEFAULT 'Y',
    product_type_id INTEGER       NOT NULL REFERENCES whatsapp_commerce.product_type(id_product_type)
);

CREATE TABLE whatsapp_commerce."order" (
    id_order          SERIAL        PRIMARY KEY,
    customer_document VARCHAR(10)   NOT NULL REFERENCES whatsapp_commerce.customer(document),
    application_date  DATE          NOT NULL,
    employe_id_card   INTEGER       REFERENCES whatsapp_commerce.employe(id_card),
    shipment_date     DATE          NOT NULL,
    discount          NUMERIC(12,2) DEFAULT 0,
    total             NUMERIC(12,2) NOT NULL,
    payment_method_id INTEGER       NOT NULL REFERENCES whatsapp_commerce.payment_method(id_payment_method)
);

CREATE TABLE whatsapp_commerce.order_detail (
    line_number       SERIAL        PRIMARY KEY,
    order_id          INTEGER       NOT NULL REFERENCES whatsapp_commerce."order"(id_order),
    customer_document VARCHAR(10)   NOT NULL,
    product_id        INTEGER       NOT NULL REFERENCES whatsapp_commerce.product(id_product),
    amount            NUMERIC(10,2) NOT NULL,
    sale_price        NUMERIC(12,2) NOT NULL,
    subtotal          NUMERIC(12,2) NOT NULL
);

CREATE TABLE whatsapp_commerce.delivery (
    id                SERIAL        PRIMARY KEY,
    place             VARCHAR(150),
    delivery_address  VARCHAR(100)  NOT NULL,
    delivery_date     DATE          NOT NULL,
    customer_document VARCHAR(10)   NOT NULL,
    hour_start        TIMESTAMP     NOT NULL,
    hour_end          TIMESTAMP,
    observation       VARCHAR(500),
    delivery_status   VARCHAR(1),
    courier_id        INTEGER       REFERENCES whatsapp_commerce.courier(id_courier),
    order_id          INTEGER       NOT NULL REFERENCES whatsapp_commerce."order"(id_order),
    value             NUMERIC(12,2) NOT NULL
);

CREATE TABLE whatsapp_commerce.credit (
    id                SERIAL        PRIMARY KEY,
    creation_date     DATE          NOT NULL,
    status            VARCHAR(1)    NOT NULL,
    customer_document VARCHAR(10)   NOT NULL,
    payment_date      DATE,
    value             NUMERIC(12,2) NOT NULL,
    order_id          INTEGER       NOT NULL REFERENCES whatsapp_commerce."order"(id_order)
);
