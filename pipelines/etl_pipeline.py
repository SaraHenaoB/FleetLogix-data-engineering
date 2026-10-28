"""
FleetLogix - Pipeline ETL Automático
Extrae de PostgreSQL, Transforma y Carga en Snowflake
Ejecución diaria automatizada
"""
import os
import psycopg2
import snowflake.connector
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import schedule
import time
import json
from typing import Dict, List, Tuple
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_pipeline.log'),
        logging.StreamHandler()
    ]
)


# Configuración de conexiones
# Encuentra la carpeta exacta donde está guardado este archivo script
BASE_DIR = Path(__file__).resolve().parent.parent
# Asigna al archivo .env dentro de esa misma carpeta
ENV_PATH = BASE_DIR / "Credentials.env"
load_dotenv(dotenv_path=ENV_PATH)


pg_conn = psycopg2.connect(
    host = os.getenv('PG_HOST'),
    database = os.getenv('PG_DATABASE'),
    user = os.getenv('PG_USER'),
    password = os.getenv('PG_PSW'),
    port = os.getenv('PG_PORT'),
)


sf_conn = snowflake.connector.connect(
    user = os.getenv('SF_USER') ,
    password = os.getenv('SF_PSW') ,
    account = os.getenv('SF_ACCOUNT'),
    warehouse = os.getenv('SF_WAREHOUSE') ,
    database = os.getenv('SF_DATABASE'),
    schema = os.getenv('SF_SCHEMA'), 
)


class FleetLogixETL:
    def __init__(self):
        self.pg_conn = None
        self.sf_conn = None
        self.batch_id = int(datetime.now().timestamp())
        self.metrics = {
            'records_extracted': 0,
            'records_transformed': 0,
            'records_loaded': 0,
            'errors': 0
        }
    
    def connect_databases(self):
        """Establecer conexiones con PostgreSQL y Snowflake"""
        try:
            # PostgreSQL
            self.pg_conn = pg_conn
            logging.info(" Conectado a PostgreSQL")
            
            # Snowflake
            self.sf_conn = sf_conn
            logging.info(" Conectado a Snowflake")
            
            return True
        except Exception as e:
            logging.error(f" Error en conexión: {e}")
            return False
    
    def extract_daily_data(self) -> pd.DataFrame:
        """Extraer datos del hace 3 hias a la ultima fecha de schedule_date anterior de PostgreSQL"""
        logging.info(" Iniciando extracción de datos...")
        
        query = """
                            
            select d.delivery_id , d.tracking_number , d.customer_name , d.package_weight_kg , 
                d.scheduled_datetime, d.delivered_datetime, d.delivery_status,
                d.recipient_signature , t.trip_id , t.departure_datetime , t.arrival_datetime,
                t.fuel_consumed_liters  , t.driver_id  , r.route_id, r.distance_km , r.toll_cost,
                r.destination_city, t.vehicle_id , v.license_plate, v.vehicle_type , v.capacity_kg, 
                v.fuel_type , v.acquisition_date, v.status as vehicle_status, m.maintenance_date ,
                d2.employee_code , concat(d2.first_name,' ', d2.last_name ) as full_name, 
                d2.license_number, d2.license_expiry , d2.phone, d2.hire_date, d2.status as driver_status , 
                r.route_code , r.origin_city 
            from deliveries d inner join trips t on d.trip_id = t.trip_id 
            inner join routes r on t.route_id = r.route_id
            inner join drivers d2 on t.driver_id = d2.driver_id
            inner join vehicles v on t.vehicle_id = v.vehicle_id
            inner join maintenance m  on m.vehicle_id = v.vehicle_id 
            where date(d.scheduled_datetime) = (select date(max(scheduled_datetime)- interval '3 day') from deliveries);
        """
        
        try:
            df = pd.read_sql(query, self.pg_conn)
            self.metrics['records_extracted'] = len(df)
            logging.info(f" Extraídos {len(df)} registros")
            return df
        except Exception as e:
            logging.error(f" Error en extracción: {e}")
            self.metrics['errors'] += 1
            return pd.DataFrame()
    ##Hasta aquí, sin errores de extracción

    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transformar datos para el modelo dimensional"""
        logging.info(" Iniciando transformación de datos...")
        
        try:
            # Calcular métricas
            df['delivery_time_minutes'] = (
                (pd.to_datetime(df['delivered_datetime']) - 
                 pd.to_datetime(df['scheduled_datetime'])).dt.total_seconds() / 60
            ).round(2)
            
            df['delay_minutes'] = df['delivery_time_minutes'].apply(
                lambda x: max(0, x) if x > 0 else 0
            )
            
            df['is_on_time'] = df['delay_minutes'] <= 30
            
            # Calcular entregas por hora
            df['trip_duration_hours'] = (
                (pd.to_datetime(df['arrival_datetime']) - 
                 pd.to_datetime(df['departure_datetime'])).dt.total_seconds() / 3600
            ).round(2)
            
            # Agrupar entregas por trip para calcular entregas/hora
            deliveries_per_trip = df.groupby('trip_id').size()
            df['deliveries_in_trip'] = df['trip_id'].map(deliveries_per_trip)
            df['deliveries_per_hour'] = (
                df['deliveries_in_trip'] / df['trip_duration_hours']
            ).round(2)
            
            # Eficiencia de combustible
            df['fuel_efficiency_km_per_liter'] = (
                df['distance_km'] / df['fuel_consumed_liters']
            ).round(2)
            
            # Costo estimado por entrega
            df['cost_per_delivery'] = (
                (df['fuel_consumed_liters'] * 5000 + df['toll_cost']) / 
                df['deliveries_in_trip']
            ).round(2)
            
            # Revenue estimado (ejemplo: $20,000 base + $500 por kg)
            df['revenue_per_delivery'] = (20000 + df['package_weight_kg'] * 500).round(2)
            
            # Validaciones de calidad
            # No permitir tiempos negativos
            df = df[df['delivery_time_minutes'] >= 0]
            
            # No permitir pesos fuera de rango
            df = df[(df['package_weight_kg'] > 0) & (df['package_weight_kg'] < 10000)]
            
            # Manejar cambios históricos (SCD Type 2 para conductor/vehículo)
            df['valid_from'] = pd.to_datetime(df['scheduled_datetime']).dt.date
            df['valid_to'] = pd.to_datetime('9999-12-31')
            df['is_current'] = True

            #Para la tabla de dim_time y dim_date
            ## Convertir a string y luego a sun entero numérico (Formato AAAAMMDD. Ej: 20260702)
            df['date_key'] = pd.to_datetime(df['scheduled_datetime']).dt.strftime('%Y%m%d').astype(int)

            # scheduled_time_key (Formato HHMM. Ej: 1320)
            df['scheduled_time_key'] = pd.to_datetime(df['scheduled_datetime']).dt.strftime('%H%M').astype(int)

            # delivered_time_key (Formato HHMM. Ej: 1320)
            df['delivered_time_key'] = pd.to_datetime(df['delivered_datetime']).dt.strftime('%H%M')
            # Si la entrega no se ha realizado, se coloca 0
            df['delivered_time_key'] = df['delivered_time_key'].fillna(0).astype(int)



            
            self.metrics['records_transformed'] = len(df)
            logging.info(f" Transformados {len(df)} registros")
            
            return df
            
        except Exception as e:
            logging.error(f" Error en transformación: {e}")
            self.metrics['errors'] += 1
            return pd.DataFrame()
        
 #### el resto de dimensiones
    def _load_dim_vehicle(self, df: pd.DataFrame):
            """Cargar dimensión de vehículos en Snowflake"""
            cursor = self.sf_conn.cursor()
            
            # Extraemos los vehículos únicos del lote actual
            vehicles = df[['vehicle_id', 'fuel_consumed_liters']].drop_duplicates()
            
            for _, row in vehicles.iterrows():
                v_id = int(row['vehicle_id'])
                # Creamos datos descriptivos simulados basados en tu mapeo analítico
                license_plate = f"ABC-{v_id:03d}"
                
                cursor.execute("""
                    MERGE INTO dim_vehicle v
                    USING (SELECT %s as vehicle_id) s
                    ON v.vehicle_id = s.vehicle_id
                    WHEN NOT MATCHED THEN
                        INSERT (vehicle_key, vehicle_id, license_plate, vehicle_type, capacity_kg, fuel_type, acquisition_date, age_months, status, is_current)
                        VALUES (%s, s.vehicle_id, %s, 'Camión Carga', 5000.00, 'Diesel', CURRENT_DATE() - 365, 12, 'Activo', TRUE);
                """, (v_id, v_id, license_plate))
            self.sf_conn.commit()

    def _load_dim_driver(self, df: pd.DataFrame):
        """Cargar dimensión de conductores en Snowflake"""
        cursor = self.sf_conn.cursor()
        drivers = df[['driver_id']].drop_duplicates()
        
        for _, row in drivers.iterrows():
            d_id = int(row['driver_id'])
            employee_code = f"EMP-{d_id:04d}"
            full_name = f"Conductor Logístico {d_id}"
            
            cursor.execute("""
                MERGE INTO dim_driver d
                USING (SELECT %s as driver_id) s
                ON d.driver_id = s.driver_id
                WHEN NOT MATCHED THEN
                    INSERT (driver_key, driver_id, employee_code, full_name, status, performance_category, is_current)
                    VALUES (%s, s.driver_id, %s, %s, 'Activo', 'Alto', TRUE);
            """, (d_id, d_id, employee_code, full_name))
        self.sf_conn.commit()

    def _load_dim_route(self, df: pd.DataFrame):
        """Cargar dimensión de rutas en Snowflake"""
        cursor = self.sf_conn.cursor()
        routes = df[['route_id', 'distance_km', 'toll_cost', 'destination_city']].drop_duplicates()
        
        for _, row in routes.iterrows():
            r_id = int(row['route_id'])
            route_code = f"RTA-{r_id:03d}"
            dist = float(row['distance_km'])
            
            cursor.execute("""
                MERGE INTO dim_route r
                USING (SELECT %s as route_id) s
                ON r.route_id = s.route_id
                WHEN NOT MATCHED THEN
                    INSERT (route_key, route_id, route_code, origin_city, destination_city, distance_km, estimated_duration_hours, toll_cost, difficulty_level, route_type)
                    VALUES (%s, s.route_id, %s, 'Bogotá', %s, %s, %s, %s, 'Medio', 'Interurbana');
            """, (r_id, r_id, route_code, row['destination_city'], dist, (dist/60), float(row['toll_cost'])))
        self.sf_conn.commit()

    

###
    def load_dimensions(self, df: pd.DataFrame):
        """Cargar o actualizar dimensiones en Snowflake"""
        logging.info(" Cargando dimensiones...")
        
        cursor = self.sf_conn.cursor()
        
        try:
            #ultimo ID para continuar
            cursor.execute("SELECT NVL(MAX(customer_key), 0) FROM dim_customer")
            current_max_key = cursor.fetchone()[0]
            # Cargar dim_customer (nuevos clientes)
            customers = df[['customer_name', 'destination_city']].drop_duplicates()
            total_customers = len(customers)
            logging.info(f" Se encontraron {total_customers} clientes únicos para procesar.")
            contador = 0
            for _, row in customers.iterrows():
                contador += 1
                current_max_key += 1 
                
                if contador % 50 == 0 or contador == total_customers:
                    logging.info(f"   -> Procesados {contador} de {total_customers} clientes...")

                # Regla de negocio para determinar el customer_type basado en el nombre
                c_name = row['customer_name']
                c_name_upper = str(c_name).upper()
                c_type = 'Empresa' if any(corp in c_name_upper for corp in ['S.A.', 'INC', 'LTDA', 'CORP']) else 'Individual'

                city_customer = row['destination_city']
                cursor.execute("""
                    MERGE INTO dim_customer c
                    USING (SELECT %s as customer_name) s
                    ON c.customer_name = s.customer_name
                    WHEN NOT MATCHED THEN
                        INSERT (customer_key, customer_name, customer_type, city, first_delivery_date, 
                               total_deliveries, customer_category)
                        VALUES (%s, s.customer_name, %s, %s, CURRENT_DATE(), 1, 'Regular')
                    WHEN MATCHED THEN
                        UPDATE SET total_deliveries = c.total_deliveries + 1;
                """, (row['customer_name'],  int(current_max_key), c_type, city_customer))
  ##          
            # cargar las otras dimensiones
            logging.info("   -> Procesando vehículos...")
            self._load_dim_vehicle(df)
            
            logging.info("   -> Procesando conductores...")
            self._load_dim_driver(df)
            
            logging.info("   -> Procesando rutas...")
            self._load_dim_route(df)
            
            cursor.close()
 ##           
            self.sf_conn.commit()
            logging.info(" Dimensiones actualizadas")
            
        except Exception as e:
            logging.error(f" Error cargando dimensiones: {e}")
            self.sf_conn.rollback()
            self.metrics['errors'] += 1
    
    def load_facts(self, df: pd.DataFrame):
        """Cargar hechos en Snowflake"""
        logging.info(" Cargando tabla de hechos...")
        
        cursor = self.sf_conn.cursor()
        
        try:

            #Mapa de Clientes (Nombre: Key)
            cursor.execute("SELECT customer_name, customer_key FROM dim_customer")
            customer_map = {row[0]: row[1] for row in cursor.fetchall()}
            # Preparar datos para inserción
            fact_data = []
            for _, row in df.iterrows():
                # Obtener keys de dimensiones
                date_key = int(pd.to_datetime(row['scheduled_datetime']).strftime('%Y%m%d'))
                scheduled_time_key = int(pd.to_datetime(row['scheduled_datetime']).strftime('%H%M'))
                
                if pd.notna(row['delivered_datetime']):
                    delivered_time_key = int(pd.to_datetime(row['delivered_datetime']).strftime('%H%M'))
                else:
                    delivered_time_key = 0

                vehicle_key = int(row['vehicle_id'])
                driver_key = int(row['driver_id']) 
                route_key = int(row['route_id'])
                
                customer_key = customer_map.get(row['customer_name'], 1)

                fact_data.append((
                    date_key,
                    scheduled_time_key,
                    delivered_time_key,
                    vehicle_key,  
                    driver_key, 
                    route_key,    
                    customer_key,
                    row['delivery_id'],
                    row['trip_id'],
                    row['tracking_number'],
                    row['package_weight_kg'],
                    row['distance_km'],
                    row['fuel_consumed_liters'],
                    row['delivery_time_minutes'],
                    row['delay_minutes'],
                    row['deliveries_per_hour'],
                    row['fuel_efficiency_km_per_liter'],
                    row['cost_per_delivery'],
                    row['revenue_per_delivery'],
                    row['is_on_time'],
                    False,  # is_damaged
                    row['recipient_signature'],
                    row['delivery_status'],
                    self.batch_id
                ))
            
            # Insertar en batch
            cursor.executemany("""
                INSERT INTO fact_deliveries (
                    date_key, scheduled_time_key, delivered_time_key,
                    vehicle_key, driver_key, route_key, customer_key,
                    delivery_id, trip_id, tracking_number,
                    package_weight_kg, distance_km, fuel_consumed_liters,
                    delivery_time_minutes, delay_minutes, deliveries_per_hour,
                    fuel_efficiency_km_per_liter, cost_per_delivery, revenue_per_delivery,
                    is_on_time, is_damaged, has_signature, delivery_status,
                    etl_batch_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, fact_data)
            
            self.sf_conn.commit()
            self.metrics['records_loaded'] = len(fact_data)
            logging.info(f" Cargados {len(fact_data)} registros en fact_deliveries")
            
        except Exception as e:
            logging.error(f" Error cargando hechos: {e}")
            self.sf_conn.rollback()
            self.metrics['errors'] += 1
    
    def run_etl(self):
        """Ejecutar pipeline ETL completo"""
        start_time = datetime.now()
        logging.info(f" Iniciando ETL - Batch ID: {self.batch_id}")
        
        try:
            # Conectar
            if not self.connect_databases():
                return
            
            # ETL
            df = self.extract_daily_data()
            if not df.empty:
                df_transformed = self.transform_data(df)
                if not df_transformed.empty:
                    self.load_dimensions(df_transformed)
                    self.load_facts(df_transformed)
            
            # Calcular totales para reportes
            self._calculate_daily_totals()
            
            # Cerrar conexiones
            self.close_connections()
            
            # Log final
            duration = (datetime.now() - start_time).total_seconds()
            logging.info(f" ETL completado en {duration:.2f} segundos")
            logging.info(f" Métricas: {json.dumps(self.metrics, indent=2)}")
            
        except Exception as e:
            logging.error(f" Error fatal en ETL: {e}")
            self.metrics['errors'] += 1
            self.close_connections()
    
    def _calculate_daily_totals(self):
        """Pre-calcular totales para reportes rápidos"""
        cursor = self.sf_conn.cursor()
        
        try:
            # Crear tabla de totales si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summary_daily_performance (
                    etl_batch_id INT,
                    total_deliveries INT,
                    avg_fuel_efficiency DECIMAL(5,2),
                    total_revenue DECIMAL(12,2),
                    total_cost DECIMAL(12,2),
                    ontime_delivery_rate DECIMAL(5,2),
                    calculated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
            """)
            
            # Insertar totales del día
            cursor.execute("""
                INSERT INTO summary_daily_performance (etl_batch_id, total_deliveries, avg_fuel_efficiency, total_revenue, total_cost, ontime_delivery_rate)
                SELECT 
                    etl_batch_id,
                    COUNT(delivery_key),
                    AVG(fuel_efficiency_km_per_liter),
                    SUM(revenue_per_delivery),
                    SUM(cost_per_delivery),
                    (COUNT(CASE WHEN is_on_time = TRUE THEN 1 END) / COUNT(delivery_key)) * 100
                FROM fact_deliveries
                WHERE etl_batch_id = %s
                GROUP BY etl_batch_id
            """, (self.batch_id,))
            
            self.sf_conn.commit()
            logging.info(" Totales diarios calculados")
            
        except Exception as e:
            logging.error(f" Error calculando totales: {e}")
    
    def close_connections(self):
        """Cerrar conexiones a bases de datos"""
        if self.pg_conn:
            self.pg_conn.close()
        if self.sf_conn:
            self.sf_conn.close()
        logging.info(" Conexiones cerradas")

def job():
    """Función para programar con schedule"""
    etl = FleetLogixETL()
    etl.run_etl()

def main():
    """Función principal - Automatización diaria"""
    logging.info(" Pipeline ETL FleetLogix iniciado")
    
    # Programar ejecución diaria a las 2:00 AM
    schedule.every().day.at("02:00").do(job)
    
    logging.info(" ETL programado para ejecutarse diariamente a las 2:00 AM")
    logging.info("Presiona Ctrl+C para detener")
    
    # Ejecutar una vez al inicio (para pruebas)
    job()
    
    # Loop infinito esperando la hora programada
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar cada minuto

if __name__ == "__main__":
    main()