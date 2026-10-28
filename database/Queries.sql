-- Query 1: Contar vehículos por tipo
-- Problema de negocio: Conocer la composición de la flota
explain analyze
select v.vehicle_type , count(v.vehicle_type ) as Cantidad
from vehicles v
Group by v.vehicle_type
order by Cantidad;

-- Query 2: Listar conductores con licencia próxima a vencer (30/60)
-- Problema de negocio: Prevenir problemas legales por licencias vencidas
explain analyze
select concat(d.first_name,' ',d.last_name )as Employee_Name, d.driver_id ,d.license_expiry ,d.status
from drivers d 
where d.license_expiry < current_date + interval '30 days'
order by d.license_expiry ;


-- Query 3: Total de viajes por estado (pending, cancelled, completados, proceso)
-- Problema de negocio: Monitorear operaciones en curso
explain analyze
select t.status, count(t.status )
from trips t
Group by status;


-- Query 4: Total de entregas por ciudad destino en los últimos 2 meses
-- Problema de negocio: Identificar demanda por ciudad para planificación de recursos
explain analyze
select r.destination_city , count(distinct t.trip_id) as Numero_De_Viajes, 
	count(d.delivery_id) as Numero_de_paquetes, sum(d.package_weight_kg) as Acumulado_Viaje_ciudad
from routes r inner join trips t on r.route_id =t.route_id 
inner join deliveries d on t.trip_id = d.trip_id 
where t.arrival_datetime > current_date - interval '60 days'
group by r.destination_city
order by numero_de_paquetes DESC; 


-- Query 5: Conductores activos con cantidad de viajes completados
-- Problema de negocio: Evaluar carga de trabajo por conductor
explain analyze
select concat(d.first_name,' ',d.last_name )as Employee_Name, d.employee_code, 
		count(t.trip_id) as Total_Trips, sum (case when t.status ='completed' then 1 else 0 end) as Completed_trips_count  
from drivers d left join trips t on d.driver_id = t.driver_id
where  d.status = 'active'
group by employee_name , d.employee_code
order by Completed_trips_count desc
limit 10; 


-- Query 6: Promedio de entregas por conductor en los últimos 6 meses
-- Problema de negocio: Medir productividad individual de conductores
explain analyze
with average_delivery 
as(
select count(del.delivery_status)/count(distinct t.driver_id) as Average_delivery_number
from drivers d inner join trips t on d.driver_id = t.driver_id 
inner join deliveries del on t.trip_id =del.trip_id
where del.delivery_status = 'delivered' and t.departure_datetime > current_date - interval '180 days'
)
select concat(d.first_name ,' ',d.last_name )as Employee_Name, d.employee_code , count(del.delivery_status) as deliver_Per_driver,
	(select Average_delivery_number from average_delivery) as Average_delivered_Per_Driver, 
	case
		when count(del.delivery_status)<(select Average_delivery_number from average_delivery) then 'Debajo del promedio' else 'Cumple'	 
	end as Performance	
from drivers d inner join trips t on d.driver_id = t.driver_id 
inner join deliveries del on t.trip_id =del.trip_id
where del.delivery_status = 'delivered' and t.departure_datetime > current_date - interval '180 days'
group by d.first_name ,d.last_name , employee_code 



-- Query 7: Rutas con mayor consumo de combustible por kilómetro
-- Problema de negocio: Identificar rutas ineficientes para optimización
explain analyze
with average_consumed (origin_city , destination_city, average_litersPerKM) as(
	select r.origin_city , r.destination_city, 
		round((sum(t.fuel_consumed_liters )/ count(r.route_id))/(sum(r.distance_km)/count(r.route_id )),2) as average_litersPerKM
	from routes r inner join trips t on r.route_id = t.route_id
	where t.status = 'completed'
	group by r.origin_city , r.destination_city 
)
select r.route_id , r.origin_city , r.destination_city, round((t.fuel_consumed_liters /r.distance_km),2) as consumed_Per_Route,
	 average_litersPerKM , 
	 case
		when round((t.fuel_consumed_liters /r.distance_km),2)>average_litersPerKM then 'Ineficiente' else 'Cumple'	 
	end as Performance
from routes r inner join trips t on r.route_id = t.route_id
inner join average_consumed ac on r.origin_city =ac.origin_city and r.destination_city =ac.destination_city 
where t.status = 'completed';



-- Query 8: Análisis de entregas retrasadas por día de la semana
-- Problema de negocio: Identificar patrones de retraso para mejorar planificación

--identificar las retrasadas. tabla deliveries  delivered_datetime>scheduled_datetime por 1 hora
--identificar el dia de la semana
--solo tener en cuenta los delivered
explain analyze
select extract(dow from d.scheduled_datetime)as ID_day, TO_CHAR(d.scheduled_datetime, 'tmday') as day_of_week, count(delivery_id) as Total_packages,
	sum(case when d.delivered_datetime> d.scheduled_datetime + interval '1 hour' then 1 else 0 end) as Delayed_packages, 
	round(100.0*(count(case 
				when d.delivered_datetime> d.scheduled_datetime + interval '1 hour' then 1 
				end))/count(delivery_id),2) as porcentage_Delayed_packages,
	round(avg( case 
		when d.delivered_datetime> d.scheduled_datetime + interval '1 hour' 
		then ((extract(epoch FROM (d.delivered_datetime - d.scheduled_datetime)) / 60)-60) else null
	end),2) as Time_delayed_min
from deliveries d
where delivery_status = 'delivered' AND d.scheduled_datetime >= CURRENT_DATE - INTERVAL '90 days'
group by ID_day, day_of_week
order by ID_day;



-- Query 9: Costo de mantenimiento por kilómetro recorrido
-- Problema de negocio: Evaluar costo-beneficio de cada tipo de vehículo
explain analyze
select v.vehicle_type, count(distinct m.vehicle_id) as Quant_vehicle , count(m.maintenance_id) as Quant_mtto, 
	sum(m."cost") as Total_cost , avg(r.distance_km) as avg_distance ,
	round(sum(m."cost")/sum(r.distance_km),2) as cost_per_KM
from maintenance m inner join vehicles v on m.vehicle_id = v.vehicle_id
left join trips t on m.vehicle_id = t.vehicle_id 
left join routes r on t.route_id = r.route_id
group by vehicle_type 
order by cost_per_KM DESC;


-- Query 10: Ranking de conductores por eficiencia usando Window Functions
-- Problema de negocio: Identificar top performers para incentivos


-- litros consumidos/ km totales/horas de viaje
-- total de paquetes entregados a tiempo/ total de paquetes
explain analyze
with trip_metrics as(
	select t.driver_id , count(distinct t.trip_id) as Total_trips,
		sum(EXTRACT(EPOCH FROM (t.arrival_datetime - t.departure_datetime)) / 3600.0) AS Trips_hours,
		sum(t.fuel_consumed_liters) as Total_fuel_comsumed,
		sum(r.distance_km ) as Total_km
	from trips t inner join routes r on t.route_id = r.route_id
	where t.status = 'completed'
	group by t.driver_id 
	),
delivery_metrics as(
	select t.driver_id , count(delivery_id) Total_of_packages,
		sum(case when del.delivered_datetime<= del.scheduled_datetime + interval '1 hour' then 1 else 0 end) as packages_ontime
	from trips t inner join deliveries del on t.trip_id = del.trip_id
	where del.delivery_status = 'delivered'
	group by t.driver_id
	)
select d.driver_id , d.employee_code , concat(d.first_name ,' ',d.last_name ),
	coalesce(Total_of_packages,0) as Total_of_packages, 
	coalesce (round(100.0 * coalesce(dm.packages_ontime, 0) / nullif(dm.Total_of_packages, 0), 2),0.00) as percentage_packages_ontime,
	coalesce (round(coalesce(dm.Total_of_packages, 0) / nullif(tm.Trips_hours, 0), 2),0.00) AS pack_per_hour,
	coalesce (round(coalesce(tm.total_fuel_comsumed, 0) / nullif(tm.Total_km, 0), 3),999.000) AS liter_per_km,
	DENSE_RANK() OVER( order by 
		coalesce (round(100.0 * coalesce(dm.packages_ontime, 0) / nullif(dm.Total_of_packages, 0), 2),0.00) DESC,
		coalesce (round(coalesce(dm.Total_of_packages, 0) / nullif(tm.Trips_hours, 0), 2),0.00) DESC,
		coalesce (round(coalesce(tm.total_fuel_comsumed, 0) / nullif(tm.Total_km, 0), 3),999.000) ASC) as ranking
from drivers d left join trip_metrics tm on d.driver_id = tm.driver_id
left join delivery_metrics dm on d.driver_id = dm.driver_id
order by ranking asc
limit 10;


-- Query 11: Análisis de tendencia de viajes con LAG y LEAD
-- Problema de negocio: Proyectar necesidades futuras basadas en tendencias
-- cuantos viajes habia conta el mes pasado para ver si hay tendencia de crecimiento
explain analyze
select TO_CHAR(t.departure_datetime, 'YYYY-MM') as Period  , count(t.trip_id ) as current_trips,
	lag(count(t.trip_id )) over(order by TO_CHAR(t.departure_datetime, 'YYYY-MM') ASC ) as previous_trips,
	count(t.trip_id )-lag(count(t.trip_id )) over(order by TO_CHAR(t.departure_datetime, 'YYYY-MM') ASC ) as Difference,
	round(100.0 * (count(t.trip_id) - lag(count(t.trip_id)) over(order by TO_CHAR(t.departure_datetime, 'YYYY-MM') ASC))
        / nullif(lag(count(t.trip_id)) over(order by TO_CHAR(t.departure_datetime, 'YYYY-MM') ASC), 0),2) as Variation_percentage
from trips t
group by TO_CHAR(t.departure_datetime, 'YYYY-MM')
order by period DESC;


-- Query 12: Pivot de entregas por hora y día de la semana
-- Problema de negocio: Optimizar horarios de operación y personal
explain analyze
select extract(hour from d.delivered_datetime) AS hora_del_dia,
    count (case when extract(DOW from d.delivered_datetime) = 1 then 1 end) AS Lunes,
    count (case when extract(DOW from d.delivered_datetime) = 2 then 1 end) AS Martes,
    count (case when extract(DOW from d.delivered_datetime) = 3 then 1 end) AS Miercoles,
    count (case when extract(DOW from d.delivered_datetime) = 4 then 1 end) AS Jueves,
    count (case when extract(DOW from d.delivered_datetime) = 5 then 1 end) AS Viernes,
    count (case when extract(DOW from d.delivered_datetime) = 6 then 1 end) AS Sabado,
    count (case when extract(DOW from d.delivered_datetime) = 0 then 1 end) AS Domingo,
    count (d.delivery_id) AS total_por_hora
from deliveries d
where d.delivery_status = 'delivered'
group by extract(hour from d.delivered_datetime)
order by hora_del_dia ASC;



