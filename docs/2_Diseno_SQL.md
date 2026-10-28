# Progress Update 2 - Query Optimization & Performance Analysis

## Query 1: Count vehicles by type
**Business Problem:** Understand FleetLogix's fleet composition.

```sql
SELECT v.vehicle_type, COUNT(v.vehicle_type) AS Cantidad
FROM vehicles v
GROUP BY v.vehicle_type
ORDER BY Cantidad;
```

### Result:
| vehicle_type | cantidad |
| --- | --- |
| Motocicleta | 20 |
| Camión Mediano | 51 |
| Camión Grande | 60 |
| Van | 69 |

### EXPLAIN ANALYZE BEFORE INDEX
```text
Sort  (cost=5.08..5.09 rows=4 width=19) (actual time=0.078..0.079 rows=4.00 loops=1)
  Sort Key: (count(vehicle_type))
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=2
  ->  HashAggregate  (cost=5.00..5.04 rows=4 width=19) (actual time=0.063..0.064 rows=4.00 loops=1)
        Group Key: vehicle_type
        Batches: 1  Memory Usage: 32kB
        Buffers: shared hit=2
        ->  Seq Scan on vehicles v  (cost=0.00..4.00 rows=200 width=11) (actual time=0.016..0.025 rows=200.00 loops=1)
              Buffers: shared hit=2
Planning Time: 0.107 ms
Execution Time: 0.123 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Sort  (cost=5.08..5.09 rows=4 width=19) (actual time=0.058..0.059 rows=4.00 loops=1)
  Sort Key: (count(vehicle_type))
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=2
  ->  HashAggregate  (cost=5.00..5.04 rows=4 width=19) (actual time=0.053..0.054 rows=4.00 loops=1)
        Group Key: vehicle_type
        Batches: 1  Memory Usage: 32kB
        Buffers: shared hit=2
        ->  Seq Scan on vehicles v  (cost=0.00..4.00 rows=200 width=11) (actual time=0.010..0.018 rows=200.00 loops=1)
              Buffers: shared hit=2
Planning:
  Buffers: shared hit=3
Planning Time: 0.112 ms
Execution Time: 0.077 ms
```

---

## Query 2: List drivers with licenses expiring soon (30/60 days)
**Business Problem:** Prevent legal issues due to expired driver licenses.

```sql
SELECT CONCAT(d.first_name, ' ', d.last_name) AS Employee_Name, d.driver_id, d.license_expiry, d.status
FROM drivers d
WHERE d.license_expiry < CURRENT_DATE + INTERVAL '30 days'
ORDER BY d.license_expiry;
```

### Result:
*Calculated based on current date June 26, 2026, showing closest expiring license belonging to Daniel Medina.*

| employee_name | driver_id | license_expiry | status |
| --- | --- | --- | --- |
| Daniel Medina | 391 | 2026-06-29 | active |
| Lorena Díaz | 27 | 2026-07-16 | active |
| Camilo Álvarez | 65 | 2026-07-16 | active |
| Joan Muñoz | 250 | 2026-07-20 | active |
| David Espitia | 239 | 2026-07-24 | active |
| Marlon González | 338 | 2026-07-24 | active |

### EXPLAIN ANALYZE BEFORE INDEX
```text
Sort  (cost=12.09..12.11 rows=6 width=47) (actual time=0.140..0.141 rows=6.00 loops=1)
  Sort Key: license_expiry
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=8
  ->  Seq Scan on drivers d  (cost=0.00..12.02 rows=6 width=47) (actual time=0.027..0.116 rows=6.00 loops=1)
        Filter: (license_expiry < (CURRENT_DATE + '30 days'::interval))
        Rows Removed by Filter: 394
        Buffers: shared hit=5
Planning:
  Buffers: shared hit=14
Planning Time: 0.222 ms
Execution Time: 0.157 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Sort  (cost=12.09..12.11 rows=6 width=47) (actual time=0.168..0.169 rows=6.00 loops=1)
  Sort Key: license_expiry
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=5
  ->  Seq Scan on drivers d  (cost=0.00..12.02 rows=6 width=47) (actual time=0.038..0.157 rows=6.00 loops=1)
        Filter: (license_expiry < (CURRENT_DATE + '30 days'::interval))
        Rows Removed by Filter: 394
        Buffers: shared hit=5
Planning:
  Buffers: shared hit=42 read=1
Planning Time: 3.236 ms
Execution Time: 0.188 ms
```

---

## Query 3: Total trips by status (pending, cancelled, completed, in progress)
**Business Problem:** Monitor ongoing operational activities.

```sql
SELECT t.status, COUNT(t.status)
FROM trips t
GROUP BY status;
```

### Result:
| status | count |
| --- | --- |
| completed | 99,816 |
| pending | 2 |
| in_progress | 182 |

### EXPLAIN ANALYZE BEFORE INDEX
```text
HashAggregate  (cost=2532.00..2532.03 rows=3 width=18) (actual time=19.221..19.222 rows=3.00 loops=1)
  Group Key: status
  Batches: 1  Memory Usage: 32kB
  Buffers: shared hit=1032
  ->  Seq Scan on trips t  (cost=0.00..2032.00 rows=100000 width=10) (actual time=0.012..3.891 rows=100000.00 loops=1)
        Buffers: shared hit=1032
Planning Time: 0.084 ms
Execution Time: 19.246 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
HashAggregate  (cost=2532.00..2532.03 rows=3 width=18) (actual time=20.077..20.078 rows=3.00 loops=1)
  Group Key: status
  Batches: 1  Memory Usage: 32kB
  Buffers: shared hit=1032
  ->  Seq Scan on trips t  (cost=0.00..2032.00 rows=100000 width=10) (actual time=0.012..4.106 rows=100000.00 loops=1)
        Buffers: shared hit=1032
Planning:
  Buffers: shared hit=31 read=1 dirtied=3
Planning Time: 2.592 ms
Execution Time: 20.105 ms
```

---

## Query 4: Total deliveries by destination city in the last 2 months
**Business Problem:** Identify demand per city for resource planning.

```sql
SELECT r.destination_city, COUNT(DISTINCT t.trip_id) AS Numero_De_Viajes,
       COUNT(d.delivery_id) AS Numero_de_paquetes, SUM(d.package_weight_kg) AS Acumulado_Viaje_ciudad
FROM routes r 
INNER JOIN trips t ON r.route_id = t.route_id
INNER JOIN deliveries d ON t.trip_id = d.trip_id
WHERE t.arrival_datetime > CURRENT_DATE - INTERVAL '60 days'
GROUP BY r.destination_city
ORDER BY numero_de_paquetes DESC;
```

### Result:
| destination_city | numero_de_viajes | numero_de_paquetes | acumulado_viaje_ciudad |
| --- | --- | --- | --- |
| Bogotá | 2,008 | 8,015 | 711,165.51 |
| Medellín | 1,915 | 7,702 | 686,041.97 |
| Cartagena | 1,645 | 6,600 | 606,246.13 |
| Cali | 1,316 | 5,337 | 472,159.96 |
| Barranquilla | 1,280 | 5,071 | 436,415.28 |

### EXPLAIN ANALYZE BEFORE INDEX
```text
-> Parallel Seq Scan on trips t (cost=0.00..2061.41 rows=4682 width=8) (actual time=17.618..19.742 rows=8025.00 loops=1)
      Filter: (arrival_datetime > (CURRENT_DATE - '60 days'::interval))
      Rows Removed by Filter: 91975
      Buffers: shared hit=1032
-> Hash (cost=1.50..1.50 rows=50 width=13) (actual time=0.543..0.543 rows=50.00 loops=3)
      Buckets: 1024 Batches: 1 Memory Usage: 11kB
      Buffers: shared hit=3
-> Seq Scan on routes r (cost=0.00..1.50 rows=50 width=13) (actual time=0.521..0.528 rows=50.00 loops=3)
      Buffers: shared hit=3
Planning:
  Buffers: shared hit=10
Planning Time: 0.775 ms
Execution Time: 254.397 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Sort (cost=17517.20..17517.22 rows=5 width=57) (actual time=254.000..254.235 rows=5.00 loops=1)
  Sort Key: (count(d.delivery_id)) DESC
  Sort Method: quicksort Memory: 25kB
  Buffers: shared hit=8361
  -> GroupAggregate (cost=13473.19..17517.15 rows=5 width=57) (actual time=245.230..254.202 rows=5.00 loops=1)
        Group Key: r.destination_city
        Buffers: shared hit=8361
        -> Gather Merge (cost=13473.19..17197.32 rows=31976 width=23) (actual time=242.069..246.339 rows=32182.00 loops=1)
              Workers Planned: 2
              Workers Launched: 2
              Buffers: shared hit=8361
Planning:
  Buffers: shared hit=60 read=2 dirtied=3
Planning Time: 5.093 ms
Execution Time: 254.402 ms
```

---

## Query 5: Active drivers with count of completed trips
**Business Problem:** Evaluate workload distribution per driver.

```sql
SELECT CONCAT(d.first_name, ' ', d.last_name) AS Employee_Name, d.employee_code,
       COUNT(t.trip_id) AS Total_Trips, SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) AS Completed_trips_count
FROM drivers d 
LEFT JOIN trips t ON d.driver_id = t.driver_id
WHERE d.status = 'active'
GROUP BY employee_name, d.employee_code
ORDER BY Completed_trips_count DESC
LIMIT 10;
```

### Result:
| employee_name | employee_code | total_trips | completed_trips_count |
| --- | --- | --- | --- |
| Humberto Cerón | EMP0037 | 312 | 310 |
| Jorge Rodríguez | EMP0006 | 305 | 305 |
| María Ramírez | EMP0256 | 305 | 304 |
| Patricia Moreno | EMP0043 | 305 | 304 |
| María Vásquez | EMP0253 | 303 | 303 |
| Aurora García | EMP0182 | 301 | 301 |
| Nancy Garcés | EMP0057 | 301 | 301 |
| Esteban Valencia | EMP0056 | 302 | 301 |
| José Garcés | EMP0143 | 302 | 301 |
| Juan Puentes | EMP0026 | 302 | 301 |

### EXPLAIN ANALYZE BEFORE INDEX
```text
Limit (cost=3723.42..3723.44 rows=10 width=56) (actual time=64.384..64.387 rows=10.00 loops=1)
  Buffers: shared hit=1037
  -> Sort (cost=3723.42..3724.35 rows=373 width=56) (actual time=64.382..64.384 rows=10.00 loops=1)
        Sort Key: (sum(CASE WHEN ((t.status)::text = 'completed'::text) THEN 1 ELSE 0 END)) DESC
        Sort Method: top-N heapsort Memory: 26kB
        Buffers: shared hit=1037
Planning Time: 0.588 ms
Execution Time: 64.453 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Limit (cost=3723.42..3723.44 rows=10 width=56) (actual time=72.582..72.585 rows=10.00 loops=1)
  Buffers: shared hit=1037
  -> Sort (cost=3723.42..3724.35 rows=373 width=56) (actual time=72.580..72.583 rows=10.00 loops=1)
        Sort Key: (sum(CASE WHEN ((t.status)::text = 'completed'::text) THEN 1 ELSE 0 END)) DESC
        Sort Method: top-N heapsort Memory: 26kB
        Buffers: shared hit=1037
Planning:
  Buffers: shared hit=13 dirtied=2
Planning Time: 0.359 ms
Execution Time: 72.665 ms
```

---

## Query 6: Average deliveries per driver in the last 6 months
**Business Problem:** Measure individual driver productivity.

```sql
WITH average_delivery AS (
    SELECT COUNT(del.delivery_status) / COUNT(DISTINCT t.driver_id) AS Average_delivery_number
    FROM drivers d 
    INNER JOIN trips t ON d.driver_id = t.driver_id
    INNER JOIN deliveries del ON t.trip_id = del.trip_id
    WHERE del.delivery_status = 'delivered' AND t.departure_datetime > CURRENT_DATE - INTERVAL '180 days'
)
SELECT CONCAT(d.first_name, ' ', d.last_name) AS Employee_Name, d.employee_code, COUNT(del.delivery_status) AS deliver_Per_driver,
       (SELECT Average_delivery_number FROM average_delivery) AS Average_delivered_Per_Driver,
       CASE 
           WHEN COUNT(del.delivery_status) < (SELECT Average_delivery_number FROM average_delivery) THEN 'Debajo del promedio' 
           ELSE 'Cumple'
       END AS Performance
FROM drivers d 
INNER JOIN trips t ON d.driver_id = t.driver_id
INNER JOIN deliveries del ON t.trip_id = del.trip_id
WHERE del.delivery_status = 'delivered' AND t.departure_datetime > CURRENT_DATE - INTERVAL '180 days'
GROUP BY d.first_name, d.last_name, employee_code;
```

### Result:
| employee_name | employee_code | deliver_per_driver | average_delivered_per_driver | performance |
| --- | --- | --- | --- | --- |
| Javier Bustos | EMP0001 | 284 | 262 | Cumple |
| Ana Barrios | EMP0002 | 269 | 262 | Cumple |
| Sandra Perdomo | EMP0003 | 264 | 262 | Cumple |
| Orlando Ospina | EMP0004 | 237 | 262 | Debajo del promedio |
| Andrés Durán | EMP0005 | 251 | 262 | Debajo del promedio |
| Jorge Rodríguez | EMP0006 | 291 | 262 | Cumple |
| Sandra Salamanca | EMP0007 | 184 | 262 | Debajo del promedio |
| Camilo Mejía | EMP0008 | 312 | 262 | Cumple |
| David Villegas | EMP0009 | 267 | 262 | Cumple |
| Nohora Ariza | EMP0010 | 269 | 262 | Cumple |
| Hernando Serrano | EMP0011 | 235 | 262 | Debajo del promedio |

### EXPLAIN ANALYZE BEFORE INDEX
```text
Finalize GroupAggregate (cost=35820.91..35943.52 rows=400 width=102) (actual time=389.553..390.387 rows=373.00 loops=1)
  Group Key: d.employee_code
  Buffers: shared hit=37542, temp read=312 written=313
Planning Time: 0.692 ms
Execution Time: 406.697 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Finalize GroupAggregate (cost=35797.13..35919.73 rows=400 width=102) (actual time=375.326..377.354 rows=373.00 loops=1)
  Group Key: d.employee_code
  Buffers: shared hit=37542, temp read=312 written=313
Planning Time: 1.375 ms
Execution Time: 409.063 ms
```

---

## Query 7: Routes with highest fuel consumption per kilometer
**Business Problem:** Identify inefficient routes for optimization.

```sql
WITH average_consumed (origin_city, destination_city, average_litersPerKM) AS (
    SELECT r.origin_city, r.destination_city,
           ROUND((SUM(t.fuel_consumed_liters) / COUNT(r.route_id)) / (SUM(r.distance_km) / COUNT(r.route_id)), 2) AS average_litersPerKM
    FROM routes r 
    INNER JOIN trips t ON r.route_id = t.route_id
    WHERE t.status = 'completed'
    GROUP BY r.origin_city, r.destination_city
)
SELECT r.route_id, r.origin_city, r.destination_city,
       ROUND((t.fuel_consumed_liters / r.distance_km), 2) AS consumed_Per_Route,
       average_litersPerKM,
       CASE 
           WHEN ROUND((t.fuel_consumed_liters / r.distance_km), 2) > average_litersPerKM THEN 'Ineficiente' 
           ELSE 'Cumple'
       END AS Performance
FROM routes r 
INNER JOIN trips t ON r.route_id = t.route_id
INNER JOIN average_consumed ac ON r.origin_city = ac.origin_city AND r.destination_city = ac.destination_city
WHERE t.status = 'completed';
```

### Result:
| route_id | origin_city | destination_city | consumed_per_route | average_litersperkm | performance |
| --- | --- | --- | --- | --- | --- |
| 29 | Cali | Medellín | 0.11 | 0.11 | Cumple |
| 35 | Barranquilla | Bogotá | 0.11 | 0.12 | Cumple |
| 41 | Barranquilla | Cali | 0.13 | 0.11 | Ineficiente |
| 42 | Barranquilla | Cali | 0.15 | 0.11 | Ineficiente |
| 28 | Cali | Medellín | 0.10 | 0.11 | Cumple |
| 38 | Barranquilla | Medellín | 0.11 | 0.11 | Cumple |
| 38 | Barranquilla | Medellín | 0.10 | 0.11 | Cumple |
| 27 | Cali | Bogotá | 0.09 | 0.11 | Cumple |
| 20 | Medellín | Barranquilla | 0.09 | 0.11 | Cumple |
| 29 | Cali | Medellín | 0.10 | 0.11 | Cumple |
| 2 | Bogotá | Medellín | 0.09 | 0.12 | Cumple |
| 34 | Cali | Cartagena | 0.10 | 0.12 | Cumple |
| 26 | Cali | Bogotá | 0.12 | 0.11 | Ineficiente |
| 13 | Medellín | Bogotá | 0.11 | 0.11 | Cumple |
| 49 | Cartagena | Medellín | 0.08 | 0.12 | Cumple |

### EXPLAIN ANALYZE BEFORE INDEX
```text
Hash Join (cost=3689.27..6794.79 rows=19964 width=118) (actual time=160.136..227.661 rows=99806.00 loops=1)
  Hash Cond: (t.route_id = r.route_id)
  Buffers: shared hit=2075
Planning Time: 0.295 ms
Execution Time: 230.428 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Hash Join (cost=3689.27..6794.79 rows=19964 width=118) (actual time=160.851..221.778 rows=99806.00 loops=1)
  Hash Cond: (t.route_id = r.route_id)
  Buffers: shared hit=2075
Planning Time: 0.622 ms
Execution Time: 224.646 ms
```

---

## Query 8: Delayed delivery analysis by day of week
**Business Problem:** Identify delay patterns to improve scheduling.

```sql
SELECT EXTRACT(DOW FROM d.scheduled_datetime) AS ID_day,
       TO_CHAR(d.scheduled_datetime, 'tmday') AS day_of_week,
       COUNT(delivery_id) AS Total_packages,
       SUM(CASE WHEN d.delivered_datetime > d.scheduled_datetime + INTERVAL '1 hour' THEN 1 ELSE 0 END) AS Delayed_packages,
       ROUND(100.0 * (COUNT(CASE WHEN d.delivered_datetime > d.scheduled_datetime + INTERVAL '1 hour' THEN 1 END)) / COUNT(delivery_id), 2) AS porcentage_Delayed_packages,
       ROUND(AVG(CASE WHEN d.delivered_datetime > d.scheduled_datetime + INTERVAL '1 hour' THEN ((EXTRACT(EPOCH FROM (d.delivered_datetime - d.scheduled_datetime)) / 60) - 60) ELSE NULL END), 2) AS Time_delayed_min
FROM deliveries d
WHERE delivery_status = 'delivered' AND d.scheduled_datetime >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY ID_day, day_of_week
ORDER BY ID_day;
```

### Result:
| id_day | day_of_week | total_packages | delayed_packages | porcentage_delayed_packages | time_delayed_min |
| --- | --- | --- | --- | --- | --- |
| 0 | sunday | 7,043 | 677 | 9.61 | 60.27 |
| 1 | monday | 7,079 | 681 | 9.62 | 60.48 |
| 2 | tuesday | 7,233 | 678 | 9.37 | 60.79 |
| 3 | wednesday | 7,161 | 700 | 9.78 | 60.01 |
| 4 | thursday | 6,775 | 646 | 9.54 | 61.17 |
| 5 | friday | 6,633 | 663 | 10.00 | 59.77 |
| 6 | saturday | 6,599 | 614 | 9.30 | 62.06 |

### EXPLAIN ANALYZE BEFORE INDEX
```text
GroupAggregate (cost=13172.61..22321.61 rows=48416 width=144) (actual time=228.970..256.563 rows=7.00 loops=1)
  Group Key: (EXTRACT(dow FROM scheduled_datetime)), (to_char(scheduled_datetime, 'tmday'::text))
  Buffers: shared hit=7386
Planning Time: 0.483 ms
Execution Time: 256.862 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
GroupAggregate (cost=16224.82..19976.39 rows=50021 width=144) (actual time=62.973..73.446 rows=7.00 loops=1)
  Group Key: (EXTRACT(dow FROM scheduled_datetime)), (to_char(scheduled_datetime, 'tmday'::text))
  Buffers: shared hit=943 read=242
Planning Time: 0.165 ms
Execution Time: 73.974 ms
```

---

## Query 9: Maintenance cost per kilometer traveled
**Business Problem:** Evaluate cost-benefit for each vehicle type.

```sql
SELECT v.vehicle_type, COUNT(DISTINCT m.vehicle_id) AS Quant_vehicle, COUNT(m.maintenance_id) AS Quant_mtto,
       SUM(m."cost") AS Total_cost, AVG(r.distance_km) AS avg_distance,
       ROUND(SUM(m."cost") / SUM(r.distance_km), 2) AS cost_per_KM
FROM maintenance m 
INNER JOIN vehicles v ON m.vehicle_id = v.vehicle_id
LEFT JOIN trips t ON m.vehicle_id = t.vehicle_id
LEFT JOIN routes r ON t.route_id = r.route_id
GROUP BY vehicle_type
ORDER BY cost_per_KM DESC;
```

### Result:
| vehicle_type | quant_vehicle | quant_mtto | total_cost | avg_distance | cost_per_km |
| --- | --- | --- | --- | --- | --- |
| Camión Mediano | 50 | 635,606 | 200,416,415,019.97 | 560.5820923969 | 562.48 |
| Van | 68 | 862,239 | 267,979,073,467.48 | 560.5724794518 | 554.42 |
| Camión Grande | 59 | 754,497 | 231,689,967,689.75 | 558.6324472331 | 549.70 |
| Motocicleta | 20 | 251,073 | 76,722,499,237.25 | 559.044011184 | 546.61 |

### EXPLAIN ANALYZE BEFORE INDEX
```text
Sort (cost=471713.61..471713.62 rows=4 width=123) (actual time=3305.721..3305.727 rows=4.00 loops=1)
  Sort Key: (round((sum(m.cost) / sum(r.distance_km)), 2)) DESC
  Sort Method: quicksort Memory: 25kB
  Buffers: shared hit=1121, temp read=27840 written=27888
Planning Time: 0.364 ms
Execution Time: 3334.980 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Sort (cost=471606.81..471606.82 rows=4 width=123) (actual time=3349.790..3349.796 rows=4.00 loops=1)
  Sort Key: (round((sum(m.cost) / sum(r.distance_km)), 2)) DESC
  Sort Method: quicksort Memory: 25kB
  Buffers: shared hit=1121, temp read=27840 written=27888
Planning Time: 4.248 ms
Execution Time: 3386.002 ms
```

---

## Query 10: Driver efficiency ranking using Window Functions
**Business Problem:** Identify top performers for performance incentives.

```sql
WITH trip_metrics AS (
    SELECT t.driver_id, COUNT(DISTINCT t.trip_id) AS Total_trips,
           SUM(EXTRACT(EPOCH FROM (t.arrival_datetime - t.departure_datetime)) / 3600.0) AS Trips_hours,
           SUM(t.fuel_consumed_liters) AS Total_fuel_comsumed,
           SUM(r.distance_km) AS Total_km
    FROM trips t 
    INNER JOIN routes r ON t.route_id = r.route_id
    WHERE t.status = 'completed'
    GROUP BY t.driver_id
),
delivery_metrics AS (
    SELECT t.driver_id, COUNT(delivery_id) AS Total_of_packages,
           SUM(CASE WHEN del.delivered_datetime <= del.scheduled_datetime + INTERVAL '1 hour' THEN 1 ELSE 0 END) AS packages_ontime
    FROM trips t 
    INNER JOIN deliveries del ON t.trip_id = del.trip_id
    WHERE del.delivery_status = 'delivered'
    GROUP BY t.driver_id
)
SELECT d.driver_id, d.employee_code, CONCAT(d.first_name, ' ', d.last_name),
       COALESCE(Total_of_packages, 0) AS Total_of_packages,
       COALESCE(ROUND(100.0 * COALESCE(dm.packages_ontime, 0) / NULLIF(dm.Total_of_packages, 0), 2), 0.00) AS percentage_packages_ontime,
       COALESCE(ROUND(COALESCE(dm.Total_of_packages, 0) / NULLIF(tm.Trips_hours, 0), 2), 0.00) AS pack_per_hour,
       COALESCE(ROUND(COALESCE(tm.total_fuel_comsumed, 0) / NULLIF(tm.Total_km, 0), 3), 999.000) AS liter_per_km,
       DENSE_RANK() OVER (
           ORDER BY COALESCE(ROUND(100.0 * COALESCE(dm.packages_ontime, 0) / NULLIF(dm.Total_of_packages, 0), 2), 0.00) DESC,
                    COALESCE(ROUND(COALESCE(dm.Total_of_packages, 0) / NULLIF(tm.Trips_hours, 0), 2), 0.00) DESC,
                    COALESCE(ROUND(COALESCE(tm.total_fuel_comsumed, 0) / NULLIF(tm.Total_km, 0), 3), 999.000) ASC
       ) AS ranking
FROM drivers d 
LEFT JOIN trip_metrics tm ON d.driver_id = tm.driver_id
LEFT JOIN delivery_metrics dm ON d.driver_id = dm.driver_id
ORDER BY ranking ASC
LIMIT 10;
```

### Result:
| driver_id | employee_code | concat | total_of_packages | percentage_packages_ontime | pack_per_hour | liter_per_km | ranking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 289 | EMP0289 | Lucy Peña | 1,058 | 92.25 | 0.48 | 0.113 | 1 |
| 386 | EMP0386 | Alejandra Montoya | 1,064 | 92.20 | 0.47 | 0.116 | 2 |
| 76 | EMP0076 | Leonor Saavedra | 1,056 | 92.14 | 0.48 | 0.116 | 3 |
| 8 | EMP0008 | Camilo Mejía | 1,131 | 92.13 | 0.48 | 0.116 | 4 |
| 359 | EMP0359 | Jesús Rangel | 922 | 92.08 | 0.46 | 0.117 | 5 |
| 320 | EMP0320 | Dora Castillo | 1,107 | 92.05 | 0.49 | 0.114 | 6 |
| 241 | EMP0241 | Deisy Guevara | 1,105 | 92.04 | 0.46 | 0.116 | 7 |
| 245 | EMP0245 | Margarita Rodríguez | 1,111 | 91.99 | 0.51 | 0.114 | 8 |
| 377 | EMP0377 | Enrique Restrepo | 1,093 | 91.95 | 0.47 | 0.115 | 9 |
| 356 | EMP0356 | Fernando Martínez | 949 | 91.89 | 0.45 | 0.116 | 10 |

### EXPLAIN ANALYZE BEFORE INDEX
```text
Limit (cost=19565.38..19565.40 rows=10 width=156) (actual time=440.290..444.553 rows=10.00 loops=1)
  Buffers: shared hit=9388
Planning Time: 0.455 ms
Execution Time: 444.775 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Limit (cost=19565.88..19565.90 rows=10 width=156) (actual time=421.512..427.037 rows=10.00 loops=1)
  Buffers: shared hit=9388
Planning Time: 0.507 ms
Execution Time: 427.250 ms
```

---

## Query 11: Trip trend analysis with LAG and LEAD
**Business Problem:** Project future operational needs based on historical trends.

```sql
SELECT TO_CHAR(t.departure_datetime, 'YYYY-MM') AS Period,
       COUNT(t.trip_id) AS current_trips,
       LAG(COUNT(t.trip_id)) OVER (ORDER BY TO_CHAR(t.departure_datetime, 'YYYY-MM') ASC) AS previous_trips,
       COUNT(t.trip_id) - LAG(COUNT(t.trip_id)) OVER (ORDER BY TO_CHAR(t.departure_datetime, 'YYYY-MM') ASC) AS Difference,
       ROUND(100.0 * (COUNT(t.trip_id) - LAG(COUNT(t.trip_id)) OVER (ORDER BY TO_CHAR(t.departure_datetime, 'YYYY-MM') ASC)) / NULLIF(LAG(COUNT(t.trip_id)) OVER (ORDER BY TO_CHAR(t.departure_datetime, 'YYYY-MM') ASC), 0), 2) AS Variation_percentage
FROM trips t
GROUP BY TO_CHAR(t.departure_datetime, 'YYYY-MM')
ORDER BY period DESC;
```

### Result:
| period | current_trips | previous_trips | difference | variation_percentage |
| --- | --- | --- | --- | --- |
| 2026-06 | 3,520 | 4,246 | -726 | -17.10 |
| 2026-05 | 4,246 | 4,110 | 136 | 3.31 |
| 2026-04 | 4,110 | 4,247 | -137 | -3.23 |
| 2026-03 | 4,247 | 3,835 | 412 | 10.74 |
| 2026-02 | 3,835 | 4,247 | -412 | -9.70 |
| 2026-01 | 4,247 | 4,246 | 1 | 0.02 |
| 2025-12 | 4,246 | 4,110 | 136 | 3.31 |
| 2025-11 | 4,110 | 4,246 | -136 | -3.20 |
| 2025-10 | 4,246 | 4,110 | 136 | 3.31 |
| 2025-09 | 4,110 | 4,247 | -137 | -3.23 |
| 2025-08 | 4,247 | 4,246 | 1 | 0.02 |
| 2025-07 | 4,246 | 4,110 | 136 | 3.31 |
| 2025-06 | 4,110 | 4,246 | -136 | -3.20 |
| 2025-05 | 4,246 | 4,110 | 136 | 3.31 |
| 2025-04 | 4,110 | 4,247 | -137 | -3.23 |
| 2025-03 | 4,247 | 3,835 | 412 | 10.74 |
| 2025-02 | 3,835 | 4,247 | -412 | -9.70 |
| 2025-01 | 4,247 | 4,246 | 1 | 0.02 |
| 2024-12 | 4,246 | 4,110 | 136 | 3.31 |
| 2024-11 | 4,110 | 4,246 | -136 | -3.20 |
| 2024-10 | 4,246 | 4,110 | 136 | 3.31 |
| 2024-09 | 4,110 | 4,247 | -137 | -3.23 |
| 2024-08 | 4,247 | 4,246 | 1 | 0.02 |
| 2024-07 | 4,246 | 590 | 3,656 | 619.66 |
| 2024-06 | 590 | [NULL] | [NULL] | [NULL] |

### EXPLAIN ANALYZE BEFORE INDEX
```text
Sort (cost=41979.14..42229.14 rows=100000 width=88) (actual time=48.448..48.450 rows=25.00 loops=1)
  Sort Key: (to_char(departure_datetime, 'YYYY-MM'::text)) DESC
  Sort Method: quicksort Memory: 26kB
  Buffers: shared hit=1032
Planning Time: 0.181 ms
Execution Time: 48.838 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
Sort (cost=41979.14..42229.14 rows=100000 width=88) (actual time=75.402..75.405 rows=25.00 loops=1)
  Sort Key: (to_char(departure_datetime, 'YYYY-MM'::text)) DESC
  Sort Method: quicksort Memory: 26kB
  Buffers: shared hit=1032
Planning Time: 0.170 ms
Execution Time: 75.875 ms
```

---

## Query 12: Delivery pivot by hour and day of week
**Business Problem:** Optimize operating hours and staffing distribution.

```sql
SELECT EXTRACT(HOUR FROM d.delivered_datetime) AS hora_del_dia,
       COUNT(CASE WHEN EXTRACT(DOW FROM d.delivered_datetime) = 1 THEN 1 END) AS Lunes,
       COUNT(CASE WHEN EXTRACT(DOW FROM d.delivered_datetime) = 2 THEN 1 END) AS Martes,
       COUNT(CASE WHEN EXTRACT(DOW FROM d.delivered_datetime) = 3 THEN 1 END) AS Miercoles,
       COUNT(CASE WHEN EXTRACT(DOW FROM d.delivered_datetime) = 4 THEN 1 END) AS Jueves,
       COUNT(CASE WHEN EXTRACT(DOW FROM d.delivered_datetime) = 5 THEN 1 END) AS Viernes,
       COUNT(CASE WHEN EXTRACT(DOW FROM d.delivered_datetime) = 6 THEN 1 END) AS Sabado,
       COUNT(CASE WHEN EXTRACT(DOW FROM d.delivered_datetime) = 0 THEN 1 END) AS Domingo,
       COUNT(d.delivery_id) AS total_por_hora
FROM deliveries d
WHERE d.delivery_status = 'delivered'
GROUP BY EXTRACT(HOUR FROM d.delivered_datetime)
ORDER BY hora_del_dia ASC;
```

### Result:
| hora_del_dia | lunes | martes | miercoles | jueves | viernes | sabado | domingo | total_por_hora |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 1,173 | 1,238 | 1,216 | 1,223 | 1,175 | 1,164 | 1,191 | 8,380 |
| 5 | 1,163 | 1,111 | 1,137 | 1,097 | 1,092 | 1,164 | 1,131 | 7,895 |
| 6 | 1,179 | 1,198 | 1,267 | 1,193 | 1,115 | 1,113 | 1,229 | 8,294 |
| 7 | 1,459 | 1,509 | 1,468 | 1,512 | 1,493 | 1,483 | 1,366 | 10,290 |
| 8 | 1,748 | 1,777 | 1,741 | 1,788 | 1,680 | 1,719 | 1,732 | 12,185 |
| 9 | 2,133 | 2,085 | 2,141 | 2,189 | 2,081 | 2,068 | 2,094 | 14,791 |
| 10 | 2,474 | 2,495 | 2,459 | 2,424 | 2,407 | 2,498 | 2,441 | 17,198 |
| 11 | 2,770 | 2,742 | 2,840 | 2,876 | 2,854 | 2,781 | 2,806 | 19,669 |
| 12 | 3,022 | 3,131 | 3,135 | 3,131 | 3,028 | 3,024 | 3,104 | 21,575 |
| 13 | 3,210 | 3,157 | 3,172 | 3,244 | 3,150 | 3,139 | 3,179 | 22,251 |
| 14 | 3,210 | 3,312 | 3,276 | 3,347 | 3,235 | 3,177 | 3,314 | 22,871 |
| 15 | 3,234 | 3,243 | 3,266 | 3,294 | 3,276 | 3,278 | 3,406 | 22,997 |
| 16 | 3,285 | 3,335 | 3,409 | 3,357 | 3,471 | 3,443 | 3,353 | 23,653 |
| 17 | 3,275 | 3,315 | 3,369 | 3,298 | 3,295 | 3,345 | 3,277 | 23,174 |
| 18 | 3,266 | 3,278 | 3,340 | 3,236 | 3,385 | 3,391 | 3,208 | 23,104 |
| 19 | 3,203 | 3,217 | 3,215 | 3,271 | 3,314 | 3,267 | 3,198 | 22,685 |
| 20 | 3,045 | 3,183 | 3,225 | 3,140 | 3,163 | 3,199 | 3,074 | 22,029 |
| 21 | 2,829 | 2,760 | 2,798 | 2,777 | 2,829 | 2,902 | 2,707 | 19,602 |
| 22 | 2,473 | 2,481 | 2,430 | 2,491 | 2,551 | 2,520 | 2,476 | 17,422 |
| 23 | 2,210 | 2,271 | 2,190 | 2,268 | 2,272 | 2,253 | 2,245 | 15,709 |

### EXPLAIN ANALYZE BEFORE INDEX
```text
GroupAggregate (cost=62733.18..91677.78 rows=398702 width=96) (actual time=207.507..658.540 rows=24.00 loops=1)
  Group Key: (EXTRACT(hour FROM delivered_datetime))
  Buffers: shared hit=7296, temp read=1471 written=1477
Planning Time: 0.145 ms
Execution Time: 681.085 ms
```

### EXPLAIN ANALYZE AFTER INDEX
```text
GroupAggregate (cost=62744.90..91696.27 rows=398860 width=96) (actual time=202.829..654.373 rows=24.00 loops=1)
  Group Key: (EXTRACT(hour FROM delivered_datetime))
  Buffers: shared hit=7296, temp read=1471 written=1477
Planning Time: 0.276 ms
Execution Time: 677.404 ms
```

---

## Created Indexes Summary

| schemaname | tablename | indexname | indexdef |
| --- | --- | --- | --- |
| public | deliveries | idx_deliveries_scheduled_datetime | CREATE INDEX idx_deliveries_scheduled_datetime ON public.deliveries USING btree (scheduled_datetime, delivery_status) WHERE ((delivery_status)::text = 'delivered'::text) |
| public | deliveries | idx_deliveries_status | CREATE INDEX idx_deliveries_status ON public.deliveries USING btree (delivery_status) |
| public | drivers | idx_drivers_status_license | CREATE INDEX idx_drivers_status_license ON public.drivers USING btree (status, license_expiry) WHERE ((status)::text = 'active'::text) |
| public | maintenance | idx_maintenance_vehicle_cost | CREATE INDEX idx_maintenance_vehicle_cost ON public.maintenance USING btree (vehicle_id, cost) |
| public | routes | idx_routes_metrics | CREATE INDEX idx_routes_metrics ON public.routes USING btree (route_id, distance_km, destination_city) |
| public | trips | idx_trips_composite_joins | CREATE INDEX idx_trips_composite_joins ON public.trips USING btree (vehicle_id, driver_id, route_id, departure_datetime) WHERE ((status)::text = 'completed'::text) |
| public | trips | idx_trips_departure | CREATE INDEX idx_trips_departure ON public.trips USING btree (departure_datetime) |
| public | vehicles | idx_vehicles_status | CREATE INDEX idx_vehicles_status ON public.vehicles USING btree (status) |

No significant search performance improvement was observed, as table size remains small compared to production datasets. Response times for most queries were slightly longer, indicating that index creation was counterproductive in this scenario.