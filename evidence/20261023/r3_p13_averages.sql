begin isolation level repeatable read read only;
show transaction_read_only;
with remessas as (
  select distinct shipment_id, delivered_date_key, carrier_key, warehouse_key,
    is_on_time, is_split_order, delivery_delay_days, transit_days, failed_attempt_count
  from analytics.fact_shipment_item where is_delivered
), exact as (
  select d.year_month, c.carrier_name, c.service_level,
    round(avg(r.transit_days), 4) as transit,
    round(avg(r.delivery_delay_days) filter (where not r.is_on_time), 4) as delay
  from remessas r
  join analytics.dim_date d on d.date_key = r.delivered_date_key
  join analytics.dim_carrier c on c.carrier_key = r.carrier_key
  join analytics.dim_warehouse w on w.warehouse_key = r.warehouse_key
  group by 1, 2, 3
), rolled as (
  select year_month, carrier_name, service_level,
    round(sum(avg_transit_days * delivered_count) / nullif(sum(delivered_count),0), 4) as transit,
    round(sum(avg_delay_days_when_late * late_count) / nullif(sum(late_count),0), 4) as delay
  from consumption.on_time_delivery_rate_by_carrier
  group by 1, 2, 3
)
select count(*) as groups_compared,
  count(*) filter (where e.transit is distinct from r.transit) as transit_differences,
  count(*) filter (where e.delay is distinct from r.delay) as delay_differences
from exact e join rolled r using (year_month, carrier_name, service_level);
rollback;
