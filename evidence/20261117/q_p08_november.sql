-- M58: what P08's cost of November 2026 is made of. P08 (consumption.gross_margin_by_category) takes
-- its cost from the sale outflows of analytics.fact_inventory_movement (is_sale), by movement month.
-- Read-only session, superuser: `ENG_DADOS_DIR=<mvp_eng_dados_2> bash evidence/20261022/ro.sh <this file>`.
begin isolation level repeatable read read only;
select * from governance.warehouse_provenance;
-- 1. Sale outflows by month, from 2026-06: movements, units, cost
select to_char(movement_date, 'YYYY-MM') as month, count(*) as movements,
       sum(quantity_out) as units_out, round(sum(cogs_amount), 2) as cogs
  from analytics.fact_inventory_movement where is_sale and movement_date >= date '2026-06-01'
 group by 1 order by 1;
-- 2. Those of 2026-11, by origin, source type and day, with the span of their occurred_at and recorded_at
select source_system, source_type, movement_date, count(*) as movements, sum(quantity_out) as units_out,
       min(occurred_at) as first_occurred, max(occurred_at) as last_occurred,
       min(recorded_at) as first_recorded, max(recorded_at) as last_recorded
  from analytics.fact_inventory_movement where is_sale and movement_date >= date '2026-11-01'
 group by 1, 2, 3 order by 1, 2, 3;
-- 3. The last order day with a realised sale, against the last sale outflow
select (select max(order_date) from analytics.fact_sales_order_item where is_realised) as last_realised_order_day,
       (select max(movement_date) from analytics.fact_inventory_movement where is_sale) as last_sale_outflow_day;
-- 4. Do the 2026-11 outflows point at shipments of orders placed before? By the month of the order behind them
select to_char(o.order_date, 'YYYY-MM') as order_month, count(distinct m.movement_id) as movements,
       sum(m.quantity_out) as units_out
  from analytics.fact_inventory_movement m
  left join analytics.fact_shipment s on m.source_type = 'shipment' and s.shipment_id::text = m.source_id
  left join (select distinct source_system, order_id, order_date from analytics.fact_sales_order_item) o
         on o.source_system = s.source_system and o.order_id = s.order_id
 where m.is_sale and m.movement_date >= date '2026-11-01'
 group by 1 order by 1;
commit;
