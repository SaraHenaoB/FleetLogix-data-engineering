# FleetLogix | End-to-End Data Engineering & Cloud Architecture

## Project Context
FleetLogix is a transportation and logistics company operating a fleet of 200 vehicles making last-mile deliveries across 5 major cities. The company has been operating with legacy systems and spreadsheets, but needs to modernize its data infrastructure to compete in today's market.

A PostgreSQL database containing the core relational model required by the company is provided. All tables must be populated with massive synthetic data respecting business relationships, queries must be developed to solve actual operational issues, and a cloud architecture must be designed to enable real-time analytics and data-driven decision-making.

## Structure

```
Proyecto_FleetLogix/
├── data/                        # Data generation scripts
│   └── data_generation.py       
│
├── database/                    # All SQL and modeling files
│   ├── fleetlogix_db_schema.sql 
│   ├── queries.sql    
│   └── dimensional_model.sql    
│
├── pipelines/                   # ETL Pipelines / Automation
│   └── etl_pipeline.py          
│
├── aws/                         # AWS Infrastructure
│   ├── aws_setup.py             
│   └── lambda_functions.py      
│
├── docs/                       
│   ├── 1_Requerimientos.md
│   ├── 2_Diseno_SQL.md
│   ├── 3_ETL_Modelado.md
│   └── 4_Arquitectura_AWS.md
│
├── .gitignore                   
├── README.md                    
└── requirements.txt             
```

## Technologies and Tools Used

- **Languages:** Python (3.x), SQL (PostgreSQL Dialect).
- **Databases & Storage:** PostgreSQL (OLTP / Source), Snowflake (Cloud Data Warehouse / Target).
- **Modeling Strategies:** Dimensional Modeling (Star / Snowflake Schema), SQL DDL.
- **Cloud Computing:** AWS (Lambda, Serverless Infrastructure Automation).
- **Development Tools:** DBeaver (Database Manager), Git/GitHub.

## Process Documentation
Detailed architecture reports and design decisions are located in the `docs/` folder:

- [1_Requerimientos](docs/1_Requerimientos.md)
- [2_Diseno_SQL](docs/2_Diseno_SQL.md)
- [3_ETL_Modelado](docs/3_ETL_Modelado.md)
- [4_Arquitectura_AWS](docs/4_Arquitectura_AWS.md)

## Execution and Deployment Guide

Follow these sequential steps to set up the local environment, populate the relational database, and execute the data pipeline.

### 1. Clone the Repository and Set Up the Environment
Open your terminal and run the following commands to clone the project, create a virtual environment, and install all necessary dependencies:

```bash
# Clone the project and navigate to the root directory
git clone https://github.com
cd Financeguard-churn-prediction

# Create and activate virtual environment (Windows)
python -m venv .venv
.venv\Scripts\activate

# Create and activate virtual environment (Mac/Linux)
# python3 -m venv .venv && source .venv/bin/activate

# Install required libraries
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Security)
The project uses a centralized credentials file to protect sensitive information.

1. In the project root, create a file named `Credentials.env`.
2. Define your PostgreSQL and Snowflake credentials using the following structure:

```ini
# PostgreSQL (Relational Database - Source)
PG_HOST=localhost
PG_DATABASE=FleetlogixDB
PG_USER=your_user
PG_PSW=your_password
PG_PORT=5432

# Snowflake (Data Warehouse - Target)
SF_USER=your_snowflake_user
SF_PSW=your_snowflake_password
SF_ACCOUNT=your_account_identifier
SF_WAREHOUSE=FLEETLOGIX_WH
SF_DATABASE=FLEETLOGIX_DW
SF_SCHEMA=ANALYTICS
```
*(Note: The `Credentials.env` file is included in `.gitignore` per industry security best practices and will never be pushed to the public repository).*

### 3. Database Population (Data Generation)
Establish a connection from DBeaver to PostgreSQL before running the scripts.

To simulate FleetLogix's massive flow of business transactions, routes, and vehicles, execute the data generator script. This process will connect to your local PostgreSQL and insert over 500,000 records while maintaining referential integrity:

```bash
python data/data_generation.py
```

### 4. ETL Pipeline Execution
Once source data is ready in PostgreSQL, execute the core automation component to extract tables, apply transformations, and load them into the Data Warehouse:

```bash
python pipelines/etl_pipeline.py
```

### 5. Database Queries

Use the queries in the `database/` folder to solve core business questions.
