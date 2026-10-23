-- RR-09: is every delivered shipment of trusted.shipments a shipment P13 counts?
-- Read-only (ro.sh). Compares by (source_system, shipment_id), not by counts.
show default_transaction_read_only;

-- Delivered shipments in trusted, by source.
select source_system, count(*) as trusted_delivered
from trusted.shipments
where is_delivered and not is_deleted
group by 1 order by 1;

-- What P13 counts, and the distinct delivered shipments of its fact.
select sum(delivered_count) as p13_delivered_count
from consumption.on_time_delivery_rate_by_carrier;

select source_system, count(distinct shipment_id) as fact_delivered
from analytics.fact_shipment_item
where is_delivered
group by 1 order by 1;

-- The two-way difference by key.
with t as (
    select source_system, shipment_id from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
)
select
    (select count(*) from t left join f using (source_system, shipment_id) where f.shipment_id is null) as trusted_only,
    (select count(*) from f left join t using (source_system, shipment_id) where t.shipment_id is null) as fact_only;

-- The trusted-only shipments: their source, their items, and whether the legacy
-- quarantine holds a record for them.
with t as (
    select * from trusted.shipments where is_delivered and not is_deleted
), f as (
    select distinct source_system, shipment_id from analytics.fact_shipment_item where is_delivered
), so as (
    select t.* from t left join f using (source_system, shipment_id) where f.shipment_id is null
)
select
    so.source_system,
    so.shipment_id,
    so.order_id,
    so.shipment_status,
    (select count(*) from trusted.shipment_items i
      where i.source_system = so.source_system and i.shipment_id = so.shipment_id) as trusted_items,
    (select count(*) from trusted.shipment_items i
      where i.source_system = so.source_system and i.shipment_id = so.shipment_id and not i.is_deleted) as live_items
from so
order by 1, 2;
