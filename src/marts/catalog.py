"""The sample project: a generic e-commerce warehouse.

Layers: raw sources -> staging (renames only) -> SCD2 dimensions ->
fact tables. All data is synthetic; no real business is represented.

Sources: customers, products, orders, order_items.
Staging: stg_customers, stg_products, stg_orders, stg_order_items.
Dimensions: dim_customer (tracked: city, segment), dim_product
  (tracked: category, unit_price).
Facts: fact_order_items (grain: one row per order line; measures
  line_total), fact_orders (grain: one row per order).
"""

from __future__ import annotations

from .models import Column, Model, ModelKind, TestDefinition

C = Column

# Raw source tables (not models): allowed as DAG roots via plan(..., external=SOURCES).
SOURCES = ("customers", "products", "orders", "order_items")


def default_models() -> list[Model]:
    return [
        Model("stg_customers", ModelKind.STAGING, ("customers",),
              (C("customer_id", ("customer_id",)), C("name", ("name",)),
               C("city", ("city",)), C("segment", ("segment",)))),
        Model("stg_products", ModelKind.STAGING, ("products",),
              (C("product_id", ("product_id",)), C("name", ("name",)),
               C("category", ("category",)), C("unit_price", ("unit_price",)))),
        Model("stg_orders", ModelKind.STAGING, ("orders",),
              (C("order_id", ("order_id",)), C("customer_id", ("customer_id",)),
               C("order_date", ("order_date",)), C("status", ("status",)))),
        Model("stg_order_items", ModelKind.STAGING, ("order_items",),
              (C("order_item_id", ("order_item_id",)), C("order_id", ("order_id",)),
               C("customer_id", ("customer_id",)), C("product_id", ("product_id",)),
               C("quantity", ("quantity",)), C("unit_price", ("unit_price",)),
               C("discount", ("discount",)))),
        Model("dim_customer", ModelKind.DIMENSION, ("stg_customers",),
              (C("customer_id", ("customer_id",)), C("name", ("name",)),
               C("city", ("city",)), C("segment", ("segment",))),
              business_key="customer_id", tracked_attributes=("city", "segment")),
        Model("dim_product", ModelKind.DIMENSION, ("stg_products",),
              (C("product_id", ("product_id",)), C("name", ("name",)),
               C("category", ("category",)), C("unit_price", ("unit_price",))),
              business_key="product_id", tracked_attributes=("category", "unit_price")),
        Model("fact_order_items", ModelKind.FACT, ("stg_order_items", "dim_customer", "dim_product"),
              (C("order_item_id", ("order_item_id",)),
               C("line_total", ("quantity", "unit_price", "discount"))),
              dimension_lookups={"customer_id": "dim_customer", "product_id": "dim_product"},
              grain_key="order_item_id",
              measures={"line_total": (("quantity", "unit_price", "discount"), "line_total")}),
        Model("fact_orders", ModelKind.FACT, ("stg_orders", "dim_customer"),
              (C("order_id", ("order_id",)),),
              dimension_lookups={"customer_id": "dim_customer"},
              grain_key="order_id"),
    ]


def default_tests() -> list[TestDefinition]:
    return [
        TestDefinition("dim_customer_key_unique", "dim_customer", "unique", "surrogate_key"),
        TestDefinition("dim_customer_id_not_null", "dim_customer", "not_null", "customer_id"),
        TestDefinition("dim_product_key_unique", "dim_product", "unique", "surrogate_key"),
        TestDefinition("fact_items_key_unique", "fact_order_items", "unique", "order_item_id"),
        TestDefinition("fact_items_customer_ref", "fact_order_items", "relationships",
                       "customer_id", "dim_customer", "customer_id"),
        TestDefinition("fact_items_product_ref", "fact_order_items", "relationships",
                       "product_id", "dim_product", "product_id"),
        TestDefinition("order_status_accepted", "stg_orders", "accepted_values", "status",
                       accepted_values=("completed", "shipped", "cancelled")),
        TestDefinition("orders_fresh", "stg_orders", "freshness", "order_date",
                       max_age_days=60, reference_time="2026-10-28T00:00:00"),
    ]
