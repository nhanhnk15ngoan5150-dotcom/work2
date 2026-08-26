from sqlalchemy import Column, Float, Integer, MetaData, String, Table

metadata = MetaData()

sales_table = Table(
    "sales",
    metadata,
    Column("order_id", String),
    Column("date", String),
    Column("store_id", String),
    Column("product_id", String),
    Column("qty", Integer),
    Column("amount", Float),
    Column("payment", String),
)

stores_table = Table(
    "stores",
    metadata,
    Column("store_id", String),
    Column("store_name", String),
    Column("category", String),
    Column("district", String),
)

products_table = Table(
    "products",
    metadata,
    Column("product_id", String),
    Column("product_name", String),
    Column("product_category", String),
    Column("unit_price", Float),
)
