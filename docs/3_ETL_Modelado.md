# Considerations for Migration to Snowflake

A star schema structure is created in Snowflake. Its definition can be found in the `dimensional_model.sql` file.

Modification was made so that `driver_key`, `route_key`, and `vehicle_key` are autosequential using `IDENTITY` to ensure unique identifiers. This also enables tracking historical changes (SCD Type 2) without deleting old records for the `dim_driver` and `dim_vehicle` tables.

In the `dim_customer` table, `customer_key` will be assigned the same value as `customer_id` to maintain structural consistency across all dimension tables.

## PostgreSQL and Snowflake Data Mapping
A data mapping exercise was performed to identify columns that transfer directly from PostgreSQL to Snowflake, offering an overview of overall distribution.

<img width="971" height="1291" alt="image" src="https://github.com/user-attachments/assets/c154e7d8-18f6-40bc-8186-b5b46943f110" />

<img width="865" height="781" alt="image" src="https://github.com/user-attachments/assets/4fceed42-fd30-4dcf-8c04-9bc50c67ad97" />

<img width="774" height="811" alt="image" src="https://github.com/user-attachments/assets/72304305-4b79-4bbf-85fd-c06e30a21660" />

<img width="975" height="614" alt="image" src="https://github.com/user-attachments/assets/097c8e8c-ed99-4d14-9cb4-2f180702c33b" />

<img width="770" height="481" alt="image" src="https://github.com/user-attachments/assets/5b06a3a3-c015-4665-8d93-28864e9cab0d" />

## Dimension Tables
The `dim_time` and `dim_date` tables will be utilized for analytics to determine delivery execution times and days, aimed at identifying night surcharges, public holidays, and overtime hours.

### `dim_time` Table
`dim_time` references 24 hours of the day broken down into minutes (1,440 minutes) that remain constant. Thus, it is loaded once directly into Snowflake using the following query:

```sql
INSERT INTO dim_time (
    time_key, hour, minute, second, time_of_day, 
    hour_24, hour_12, am_pm, is_business_hour, shift
)
SELECT 
    ((hour * 100) + minute)::INT as time_key,
    hour,
    minute,
    0 as second,
    CASE 
        WHEN hour BETWEEN 0 AND 5 THEN 'Madrugada'
        WHEN hour BETWEEN 6 AND 11 THEN 'Mañana'
        WHEN hour BETWEEN 12 AND 17 THEN 'Tarde'
        ELSE 'Noche'
    END as time_of_day,
    LPAD(hour, 2, '0') || ':' || LPAD(minute, 2, '0') as hour_24,
    TO_CHAR(TIME_FROM_PARTS(hour, minute, 0), 'HH12:MI AM') as hour_12,
    TO_CHAR(TIME_FROM_PARTS(hour, minute, 0), 'AM') as am_pm,
    IFF(hour BETWEEN 8 AND 17, TRUE, FALSE) as is_business_hour,
    CASE 
        WHEN hour BETWEEN 6 AND 13 THEN 'Turno 1'  -- Mañana (06:00 - 14:00)
        WHEN hour BETWEEN 14 AND 21 THEN 'Turno 2' -- Tarde (14:00 - 22:00)
        ELSE 'Turno 3'                             -- Nocturno (22:00 - 06:00)
    END as shift
FROM (
    SELECT 
        FLOOR((ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1) / 60) as hour,
        MOD((ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1), 60) as minute
    FROM TABLE(GENERATOR(ROWCOUNT => 1440))
);
```

### `dim_date` Table
`dim_date` is constructed for a 4-year span directly in Snowflake, incorporating official Colombian holidays for each year via the following query:

```sql
INSERT INTO dim_date (
    date_key, full_date, day_of_week, day_name, day_of_month,
    day_of_year, week_of_year, month_num, month_name, quarter, year,
    is_weekend, is_holiday, holiday_name, fiscal_quarter, fiscal_year
)
SELECT 
    TO_CHAR(gen.d, 'YYYYMMDD')::INT as date_key,
    gen.d as full_date,
    DAYOFWEEKISO(gen.d) as day_of_week,
    DAYNAME(gen.d) as day_name,
    DAY(gen.d) as day_of_month,
    DAYOFYEAR(gen.d) as day_of_year,
    WEEKOFYEAR(gen.d) as week_of_year,
    MONTH(gen.d) as month_num,
    MONTHNAME(gen.d) as month_name,
    QUARTER(gen.d) as quarter,
    YEAR(gen.d) as year,
    IFF(DAYOFWEEKISO(gen.d) IN (6, 7), TRUE, FALSE) as is_weekend,
    -- Turn on analytical flag if matching on-the-fly list
    IFF(h.holiday_date IS NOT NULL, TRUE, FALSE) as is_holiday,
    NVL(h.holiday_name, 'Día Común') as holiday_name,
    QUARTER(gen.d) as fiscal_quarter,
    YEAR(gen.d) as fiscal_year
FROM (
    -- Mathematical generator for 5 years (1,826 days)
    SELECT DATEADD(day, ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1, '2024-01-01'::DATE) as d
    FROM TABLE(GENERATOR(ROWCOUNT => 1826))
) gen
LEFT JOIN (
    -- On-the-fly list of Official Colombian Holidays without auxiliary tables
    SELECT TO_DATE(column1) as holiday_date, column2 as holiday_name
    FROM VALUES 
        -- 2024
        ('2024-01-01', 'Año Nuevo'), ('2024-01-08', 'Reyes Magos'), ('2024-03-25', 'Día de San José'),
        ('2024-03-28', 'Jueves Santo'), ('2024-03-29', 'Viernes Santo'), ('2024-05-01', 'Día del Trabajo'),
        ('2024-05-13', 'Ascensión de Jesús'), ('2024-06-03', 'Corpus Christi'), ('2024-06-10', 'Sagrado Corazón de Jesús'),
        ('2024-07-01', 'San Pedro y San Pablo'), ('2024-07-20', 'Día de la Independencia'), ('2024-08-07', 'Batalla de Boyacá'),
        ('2024-08-19', 'Asunción de la Virgen'), ('2024-10-14', 'Día de la Raza'), ('2024-11-04', 'Todos los Santos'),
        ('2024-11-11', 'Independencia de Cartagena'), ('2024-12-08', 'Inmaculada Concepción'), ('2024-12-25', 'Navidad'),
        -- 2025
        ('2025-01-01', 'Año Nuevo'), ('2025-01-06', 'Reyes Magos'), ('2025-03-24', 'Día de San José'),
        ('2025-04-17', 'Jueves Santo'), ('2025-04-18', 'Viernes Santo'), ('2025-05-01', 'Día del Trabajo'),
        ('2025-06-02', 'Ascensión de Jesús'), ('2025-06-23', 'Corpus Christi'), ('2025-06-30', 'Sagrado Corazón de Jesús'),
        ('2025-06-16', 'San Pedro y San Pablo'), ('2025-07-20', 'Día de la Independencia'), ('2025-08-07', 'Batalla de Boyacá'),
        ('2025-08-18', 'Asunción de la Virgen'), ('2025-10-13', 'Día de la Raza'), ('2025-11-03', 'Todos los Santos'),
        ('2025-11-17', 'Independencia de Cartagena'), ('2025-12-08', 'Inmaculada Concepción'), ('2025-12-25', 'Navidad'),
        -- 2026
        ('2026-01-01', 'Año Nuevo'), ('2026-01-12', 'Reyes Magos'), ('2026-03-23', 'Día de San José'),
        ('2026-04-02', 'Jueves Santo'), ('2026-04-03', 'Viernes Santo'), ('2026-05-01', 'Día del Trabajo'),
        ('2026-05-18', 'Ascensión de Jesús'), ('2026-06-08', 'Corpus Christi'), ('2026-06-15', 'Sagrado Corazón de Jesús'),
        ('2026-06-29', 'San Pedro y San Pablo'), ('2026-07-20', 'Día de la Independencia'), ('2026-08-07', 'Batalla de Boyacá'),
        ('2026-08-17', 'Asunción de la Virgen'), ('2026-10-12', 'Día de la Raza'), ('2026-11-02', 'Todos los Santos'),
        ('2026-11-16', 'Independencia de Cartagena'), ('2026-12-08', 'Inmaculada Concepción'), ('2026-12-25', 'Navidad'),
        -- 2027
        ('2027-01-01', 'Año Nuevo'), ('2027-01-11', 'Reyes Magos'), ('2027-03-22', 'Día de San José'),
        ('2027-03-25', 'Jueves Santo'), ('2027-03-26', 'Viernes Santo'), ('2027-05-01', 'Día del Trabajo'),
        ('2027-05-10', 'Ascensión de Jesús'), ('2027-05-31', 'Corpus Christi'), ('2027-06-07', 'Sagrado Corazón de Jesús'),
        ('2027-06-14', 'San Pedro y San Pablo'), ('2027-07-20', 'Día de la Independencia'), ('2027-08-07', 'Batalla de Boyacá'),
        ('2027-08-16', 'Asunción de la Virgen'), ('2027-10-18', 'Día de la Raza'), ('2027-11-01', 'Todos los Santos'),
        ('2027-11-15', 'Independencia de Cartagena'), ('2027-12-08', 'Inmaculada Concepción'), ('2027-12-25', 'Navidad'),
        -- 2028
        ('2028-01-01', 'Año Nuevo'), ('2028-01-10', 'Reyes Magos'), ('2028-03-20', 'Día de San José'),
        ('2028-04-13', 'Jueves Santo'), ('2028-04-14', 'Viernes Santo'), ('2028-05-01', 'Día del Trabajo'),
        ('2028-05-29', 'Ascensión de Jesús'), ('2028-06-19', 'Corpus Christi'), ('2028-06-26', 'Sagrado Corazón de Jesús'),
        ('2028-07-03', 'San Pedro y San Pablo'), ('2028-07-20', 'Día de la Independencia'), ('2028-08-07', 'Batalla de Boyacá'),
        ('2028-08-21', 'Asunción de la Virgen'), ('2028-10-16', 'Día de la Raza'), ('2028-11-06', 'Todos los Santos'),
        ('2028-11-13', 'Independencia de Cartagena'), ('2028-12-08', 'Inmaculada Concepción'), ('2028-12-25', 'Navidad')
) h ON gen.d = h.holiday_date;
```

Remaining metrics for the fact table are processed within the `def transform_data` function.