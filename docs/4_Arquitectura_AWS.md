# Data Architecture

## AWS Architecture Diagram

<img width="975" height="633" alt="image" src="https://github.com/user-attachments/assets/e018ef32-a169-48d2-b83d-22fe2882577c" />

## How would FleetLogix benefit from implementing AWS services?

Implementing these services for the FleetLogix database yields key benefits:
* It establishes a scalable architecture. By using **API Gateway** and **AWS Lambda**, the company eliminates overhead associated with maintaining raw server infrastructure or running out of storage/compute capacity. The company has only been operating for 2 years, allowing it to continue OLTP processing while preparing for increased query and analytical reporting demands.
* It prevents RAM saturation during traffic spikes or peak-hour truck/delivery tracking, automatically adjusting compute capacity to match real-time requirements.
* Serverless data pipelines using Lambda functions enable storing raw data, error logs, or unformatted payloads directly in **Amazon S3** (Simple Storage Service), transforming and writing data to **Amazon RDS** (which simplifies traditional relational database management with minimal setup), alongside **DynamoDB** to store high-priority real-time tracking and status queries for low-latency retrieval.
* **CloudWatch** provides real-time visibility into system anomalies or failures through aggregated API Gateway logs and error monitoring across Lambda functions.
* The unified integration of API Gateway, Lambda, S3, RDS, and DynamoDB—paired with monitoring and automated backups—establishes a robust, secure, and scalable data ecosystem.

---

### Questions & Deep Dives

#### a. What resources are created in `lambda_functions.py` and `aws_setup.py`, and what functionality does each have?
#### b. Deep dive into the `verificar-entrega` (verify-delivery) Lambda function.
#### c. Deep dive into the `migrar_datos_postgresql()` function.

Lambda functions operate on data registered within FleetLogix, accepting JSON payloads and executing validations/actions:

* **Lambda 1 (`verificar-entrega`):** Checks whether a delivery is completed by consuming delivery status and tracking number. If completed, it returns delivery ID, tracking number, status, and delivery timestamp. Otherwise, it returns a 404 error: `"Delivery not found"`.
* **Lambda 2:** Calculates estimated time of arrival (ETA). Using vehicle ID, current location, destination, and speed, it computes estimated arrival time and updates the `'vehicle_tracking'` table in DynamoDB. If required fields are missing, it throws an error: `'Missing required parameters'`.
* **Lambda 3:** Dispatches alerts if a vehicle deviates from its route. Consuming vehicle ID, current location, route, and driver, it verifies route waypoints to determine destination latitude and longitude. If deviation exceeds 5 km, it raises an alert message: `"Alert: Route Deviation Detected"` containing vehicle metadata, and logs the event in the `'alerts_history'` table in DynamoDB. If the route is missing or invalid parameters are passed, it returns `'error': 'Route not found'` or `'error': 'Missing required parameters'` respectively.

---

### Setup and Migration Script (`aws_setup.py`)

`aws_setup.py` configures core AWS infrastructure, account security policies, and production database provisioning:
* Provisions an RDS PostgreSQL instance in AWS configured with compute allocation and automated backups.
* Creates an S3 bucket for historical data storage.
* Provisions DynamoDB tables (resources): `'deliveries_status'`, `'vehicle_tracking'`, `'routes_waypoints'`, and `'alerts_history'`.
* **`migrar_datos_postgresql()`:** Connects to the local FleetLogix PostgreSQL database, performs a full data dump exported to a `.sql` file, provisions an AWS RDS instance, and imports the data so the cloud environment mirrors local development.
* Provisions an IAM role for Lambda functions, granting least-privilege permissions for cross-service communication.