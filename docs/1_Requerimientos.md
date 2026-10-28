# Analysis of the Provided Model

## Context

FleetLogix is a transport and logistics company operating a fleet of 200 vehicles making last-mile deliveries across 5 major cities. The company has been operating with legacy systems and spreadsheets, but needs to modernize its data infrastructure to compete in today's market.

## FleetLogix Entity-Relationship Diagram

<img width="1173" height="840" alt="image" src="https://github.com/user-attachments/assets/d48a62c9-6e4e-4838-b7d8-4ace6d318ef4" />

### Relationship / Cardinality Explanation:
* A delivery may or may not be associated with a trip.
* A trip can have one or many deliveries assigned.
* A trip may or may not be assigned to a driver.
* A driver can be assigned to one or many trips.
* A trip may or may not be assigned to a route.
* A route must have at least one associated trip.
* A trip may or may not be assigned to a vehicle.
* A vehicle can be assigned to 1 or many trips.
* A specific maintenance record may or may not be assigned to a vehicle.
* A vehicle can have 1 or many associated maintenance records.

### Key Table Relationships

| Table 1 / Primary Key | Table 2 Connection / Primary Key | Foreign Key |
| --- | --- | --- |
| `deliveries.delivery_id` | `trips.trip_id` | `trip_id` |
| `drivers.driver_id` | `trips.trip_id` | `driver_id` |
| `routes.route_id` | `trips.trip_id` | `route_id` |
| `vehicles.vehicle_id` | `trips.trip_id` | `vehicle_id` |
| `maintenance.maintenance_id` | `vehicles.vehicle_id` | `vehicle_id` |

### Relationships and Constraints

#### `vehicles` table (Fleet vehicles):
* Primary key `vehicle_id` recognizes each vehicle as unique using an autoincrement counter and creates an index for it.
* `license_plate` values are unique and must be registered; null values are not accepted.
* Registered trucks are active by default unless specified otherwise.

#### `drivers` table (Drivers):
* Primary key `driver_id`; no other driver with the same identification can exist within the company; creates an index to facilitate searching.
* `employee_code` and `license_number` must be unique and registered; null values are not accepted.
* First name (`first_name`) and last name (`last_name`) must be registered; empty fields are not accepted.
* All registered drivers are active by default unless specified otherwise.

#### `routes` table (Predefined routes):
* Primary key `route_id`; no route with the same identification can exist; creates an index for it.
* `route_code` only allows unique, registered values; nulls are not allowed.
* Origin city and destination city must be registered obligatorily.
* Total cost is set to $0 if not specified.

#### `trips` table (Completed trips):
* Each trip has an automatically generated identifier; an index is created.
* For a trip to exist, there must first be an assigned vehicle, designated driver(s), and a route associated with that trip.
* Trip departure date and time must be specified.
* Trip status is set to `in_progress` by default.

#### `deliveries` table (Individual deliveries):
* Each individual delivery has a generated unique identifier. An index is created to facilitate searching.
* The delivery accepts empty values, and if a value is entered, the reference must exist in the `trips` table.
* The tracking number (`tracking_number`) must be unique and cannot be empty.
* Customer name (`customer_name`) and delivery address (`delivery_address`) must be registered; null values are not accepted.
* Delivery status will be `"pending"` unless specified otherwise.
* Recipient signature status accepts `"True"`, `"False"`, and null values.

#### `maintenance` table (Vehicle maintenance):
* Each maintenance record has a unique identifier. An internal index is created to facilitate searching.
* The identifier of the vehicle undergoing maintenance can be registered or left unassigned.
* Maintenance date and maintenance type do not accept null values, indicating that these are future scheduled maintenance events in cases where a vehicle has not yet been assigned.

### Indexes

```sql
CREATE INDEX idx_trips_departure ON trips(departure_datetime);
CREATE INDEX idx_deliveries_status ON deliveries(delivery_status);
CREATE INDEX idx_vehicles_status ON vehicles(status);
```

These indexes help speed up queries regarding trip status, package status, and vehicle status.

### Implicit Business Patterns

From the relationships between tables, it can be inferred that the operating model consists of accepting orders or packages in advance bound for a specified destination city. FleetLogix accepts the order and can schedule the trip in which it will be sent, the driver(s) in charge of that freight, and assign it to a predefined route. It does not need to have all information at the moment of accepting the shipment. In this manner, it can plan the delivery of packages sharing a common or nearby destination, maximizing resources and avoiding waste and inefficient operations.

### Findings / Possible Improvements

* Place a constraint on vehicle status to only accept values of `Active`, `Inactive`, or `In Maintenance`.
* For driver status, restrict allowed values to `Active`, `Inactive`, `Retired`, `On Vacation`, or `Disability`.
* For delivery status, restrict values to standard operational statuses.
* For trip status, allow only values such as `Not_started`, `in_progress`, `canceled`, or `completed`.
* Regarding the maintenance table, based on business requirements stating that maintenance must occur every 20 trips, a historical record must obligatorily have `vehicle_id` registered; maintenance cannot be performed on a non-existent vehicle. Furthermore, because maintenance frequency is defined, execution dates for predictive and preventive maintenance can be scheduled for each registered vehicle. Therefore, `vehicle_id` should also be required in these cases. It is recommended to disallow null values for `vehicle_id` in the maintenance table:

  ```sql
  vehicle_id INTEGER NOT NULL REFERENCES vehicles(vehicle_id)
  ```

  *Note to whom it may concern:* This changes the relationship from `0..1` to `1..n` between `maintenance` and `vehicles`, where a vehicle can have one or many associated maintenance records, but never null. For a new vehicle, it is recommended to register the first maintenance date at 2 months as required by Colombian regulation [1].

* A table for authorized maintenance personnel should be added to maintain audit control over individuals interacting with vehicles.

### Synthetic Data Generation

* For the 6 tables mentioned above.
* To complete the `routes` table for 50 trips. Medellín and Bogotá are considered to have 3 routes if they are the origin or destination, as they are high-commerce cities.
* To distribute completed trips:

  ```python
  # Status (95% completed)
  if arrival < datetime.now() - timedelta(days=1):
      status = 'completed'
  elif departure > datetime.now():
      status = 'pending'
  else:
      status = 'in_progress'
  ```

  ```python
  # Remove int() to avoid losing days due to decimal parts
  current_date += timedelta(minutes=int(1440 * 2 * 365 / count))
  ```

* A modification was made to the delivery counter to calculate exactly 4,000 deliveries using `>=` so it does not iterate over extra records:

  ```python
  if delivery_counter >= count:
      break
  ```

* In `maintenance`, the following statement:

  ```python
  num_maintenance = max(1, trip_count // 20)
  ```

  was replaced by:

  ```python
  num_maintenance = math.ceil(trip_count / 20) if trip_count > 0 else 1
  ```

  This accounts for trips already accumulated by the vehicle and rounds up to the nearest integer if division yields decimals. If the vehicle is new with 0 trips, it defaults to 1 regulatory maintenance.

#### `generate_trips()` Method
This method first queries `vehicle`, `driver`, and `route` tables to verify active status and retrieves distance, estimated duration, and truck capacity. It generates dates up to 2 years prior to the current date. It then enters a `for` loop to generate trips. Selected query values are randomized using `random`, and trip departure time is generated via the `gethourly_distribution()` auxiliary method. With randomized departure and arrival times, trip duration is determined.

#### `gethourly_distribution()` Auxiliary Method
This helper method (prefixed with `_`) was created to assign trip departure hours based on probability, assigning higher probabilities to peak working hours and choosing an hour according to those probabilities using `random`.

## Bibliography
[1] Article 3. Resolution 315 of 2013, Ministry of Transport of Colombia.