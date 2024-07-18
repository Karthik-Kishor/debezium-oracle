
# Oracle CDC using Debezium

Change Data Capture (CDC) is a method for tracking row-level changes in database tables resulting from create, update, and delete operations. **Debezium** is a distributed platform that leverages CDC capabilities from various databases. It offers a suite of **Kafka Connect** connectors that capture row-level changes and transform them into event streams, which are subsequently sent to **Apache Kafka**. This project will guide you through setting up CDC using [Azure Event Hubs](https://azure.microsoft.com/en-in/products/event-hubs/), [Oracle](https://www.oracle.com/) and [Debezium v1.9](https://debezium.io/documentation/reference/1.9/).


### Architecture

![Architecture Screenshot](https://github.com/Karthik-Kishor/debezium-oracle/blob/Main/images/architecture.png)


## Prerequisites

- Azure subscription
- Docker
- Python

## Run Locally

1. Clone this [repo](https://github.com/Karthik-Kishor/debezium-oracle.git)

2. Create a new Python virtual environment.

3. Activate the newly created virtual environment and run 
```bash
pip install -r requirements.txt
```
    
## Create Azure resources

1. Visit [Microsoft Azure](https://portal.azure.com) and create a new Azure Resource Group. 

2. Within this Resource Group, set up an Azure Event Hubs. 

3. After the Event Hub is created, navigate to **Shared access policies** under the Settings section.

![Azure Screenshot](https://github.com/Karthik-Kishor/debezium-oracle/blob/Main/images/eventhubs-settings.jpeg)

4. By default, the policy used is **RootManageSharedAccessKey**. If needed, you can create a different policy. 

5. Click on **RootManageSharedAccessKey** and copy either the Primary or Secondary Connection String. 

![Azure Screenshot](https://github.com/Karthik-Kishor/debezium-oracle/blob/Main/images/policy-keys.jpeg)

6. Add the Event Hubs Namespace and Connection String to the .env file in the cloned repo. [Refer Environment Variables](https://github.com/Karthik-Kishor/debezium-oracle?tab=readme-ov-file#environment-variables)


## Run the docker compose file

If you do not have an Oracle account, visit [Oracle Container Registry](https://container-registry.oracle.com/) and sign up.

After creating your Oracle account, test your Docker login by running the following command.

```
docker login container-registry.oracle.com

Username: your username or email
Password: your password
```

Once logged in successfully, run the following command to pull the Oracle and Debezium images and start the containers.

```bash
docker compose up --build
```

Open a terminal to the Oracle database container. You will use SQL*Plus to connect to the database within this container.

```bash
docker exec -it oracle sqlplus sys/oraclepw as sysdba
```
## Setting up Oracle

These instructions detail the necessary steps to configure Oracle for use with the Debezium Oracle connector, assuming a multi-tenancy setup with a container database and at least one pluggable database.

### Preparing the database

#### Configuration needed for Oracle LogMiner

Execute the following commands to configure Oracle LogMiner.

```bash
ALTER SYSTEM SET db_recovery_file_dest_size = 10G;

ALTER SYSTEM SET db_recovery_file_dest = '/opt/oracle/oradata/ORCL' scope=spfile;

SHUTDOWN IMMEDIATE;

STARTUP MOUNT;

ALTER DATABASE ARCHIVELOG;

ALTER DATABASE OPEN;

ARCHIVE LOG LIST;
```

#### Redo log sizing 

Before deploying the Debezium Oracle connector, it is essential to review and optimize your database's redo log configuration to ensure peak performance. Inadequate redo log size or count can lead to performance bottlenecks. The redo log capacity must be sufficient to accommodate the database's data dictionary, which expands with the number of tables and columns. Inadequate redo logs can adversely affect both the database and the Debezium connector. 

```bash
ALTER DATABASE CLEAR LOGFILE GROUP 1;

ALTER DATABASE DROP LOGFILE GROUP 1;

ALTER DATABASE ADD LOGFILE GROUP 1 ('/opt/oracle/oradata/ORCL/redo01.log') size 400M REUSE;

ALTER SYSTEM SWITCH LOGFILE;
```

#### Supplemental logging (Database level)

Oracle does not provide supplemental log data by default. Since Debezium relies on LogMiner, it is crucial to enable supplemental logging to allow Debezium to capture any change data.

```bash
ALTER DATABASE ADD SUPPLEMENTAL LOG DATA;
```

#### Creating users for the connector 

To capture change events, the Debezium Oracle connector must run as an Oracle LogMiner user with specific permissions. Use the following commands to create the necessary users and tablespaces.

```bash
CONNECT sys/oraclepw@ORCL as sysdba;

CREATE TABLESPACE logminer_tbs DATAFILE '/opt/oracle/oradata/ORCL/logminer_tbs.dbf' SIZE 25M REUSE AUTOEXTEND ON MAXSIZE UNLIMITED;
```

```bash
CONNECT sys/oraclepw@ORCLPDB as sysdba;

CREATE TABLESPACE logminer_tbs DATAFILE '/opt/oracle/oradata/ORCL/ORCLPDB/logminer_tbs.dbf' SIZE 25M REUSE AUTOEXTEND ON MAXSIZE UNLIMITED;
```

```bash
CONNECT sys/oraclepw@ORCL as sysdba;

CREATE USER c##dbzuser IDENTIFIED BY dbz DEFAULT TABLESPACE LOGMINER_TBS QUOTA UNLIMITED ON LOGMINER_TBS CONTAINER=ALL;

GRANT CREATE SESSION TO c##dbzuser CONTAINER=ALL;

GRANT SET CONTAINER TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$DATABASE TO c##dbzuser CONTAINER=ALL;

GRANT FLASHBACK ANY TABLE TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ANY TABLE TO c##dbzuser CONTAINER=ALL;

GRANT SELECT_CATALOG_ROLE TO c##dbzuser CONTAINER=ALL;

GRANT EXECUTE_CATALOG_ROLE TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ANY TRANSACTION TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ANY DICTIONARY TO c##dbzuser CONTAINER=ALL;

GRANT LOGMINING TO c##dbzuser CONTAINER=ALL;

GRANT CREATE TABLE TO c##dbzuser CONTAINER=ALL;

GRANT LOCK ANY TABLE TO c##dbzuser CONTAINER=ALL;

GRANT CREATE SEQUENCE TO c##dbzuser CONTAINER=ALL;

GRANT EXECUTE ON DBMS_LOGMNR TO c##dbzuser CONTAINER=ALL;

GRANT EXECUTE ON DBMS_LOGMNR_D TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$LOG TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$LOG_HISTORY TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$LOGMNR_LOGS TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$LOGMNR_CONTENTS TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$LOGMNR_PARAMETERS TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$LOGFILE TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$ARCHIVED_LOG TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$ARCHIVE_DEST_STATUS TO c##dbzuser CONTAINER=ALL;

GRANT SELECT ON V_$TRANSACTION TO c##dbzuser CONTAINER=ALL;

exit
```

## Create some initial test data

In a new terminal, connect to the database using SQL*Plus and create a new table with some initial data. Follow these steps.

Connect to the Oracle database
```bash
docker exec -it oracle sqlplus c##dbzuser/dbz@ORCLPDB
```

Create the `Customers` table with the following SQL commands.
```bash
CREATE TABLE Customers (customer_id number(10) PRIMARY KEY NOT NULL, 
first_name varchar2(50) NULL, 
last_name varchar2(50) NULL, 
email varchar2(100) UNIQUE, 
modified_date date NOT NULL);

INSERT INTO Customers VALUES (6194, 'John', 'Doe', 'john.doe@example.com', SYSDATE);
INSERT INTO Customers VALUES (2569, 'Jane', 'Smith', 'jane.smith@example.com', SYSDATE);
INSERT INTO Customers VALUES (3269, 'Bob', 'Johnson', 'bob.johnson@example.com', SYSDATE);
INSERT INTO Customers VALUES (4129, 'Alice', 'Wilson', 'alice.wilson@example.com', SYSDATE);
INSERT INTO Customers VALUES (5015, 'Charlie', 'Brown', 'charlie.brown@example.com', SYSDATE);

COMMIT;
```

Create the `Products` table with the following SQL commands.
```bash
CREATE TABLE Products (
product_id number(10) PRIMARY KEY,
product_name varchar2(100) UNIQUE,
price number(10) NULL,
modified_date date NOT NULL
);

INSERT INTO Products VALUES (1296, 'Widget A', 10, SYSDATE);
INSERT INTO Products VALUES (2394, 'Widget B', 15, SYSDATE);
INSERT INTO Products VALUES (3129, 'Widget C', 19, SYSDATE);
INSERT INTO Products VALUES (4008, 'Gadget X', 29, SYSDATE);
INSERT INTO Products VALUES (5297, 'Gadget Y', 39, SYSDATE);
INSERT INTO Products VALUES (63399, 'Accessory 1', 5, SYSDATE);
INSERT INTO Products VALUES (7856, 'Accessory 2', 7, SYSDATE);
INSERT INTO Products VALUES (8297, 'Accessory 3', 9, SYSDATE);
INSERT INTO Products VALUES (9364, 'Widget D', 12, SYSDATE);
INSERT INTO Products VALUES (1027, 'Gadget Z', 49, SYSDATE);

COMMIT;
```
Create the `Orders` table with the following SQL commands.
```bash
CREATE TABLE Orders (
order_id number(10) PRIMARY KEY,
product_id number(10) NOT NULL,
customer_id number(10) NOT NULL,
order_date DATE NULL,
quantity number(10) NULL,
total_amount number(10) NULL,
modified_date date NOT NULL,
CONSTRAINT orders_fk
FOREIGN KEY (customer_id)
REFERENCES Customers(customer_id)
);

INSERT INTO Orders VALUES (1, 1296, 2569, to_date('2023-01-15', 'yyyy-mm-dd'), 3, 32, SYSDATE);
INSERT INTO Orders VALUES (2, 3129, 6194, to_date('2023-02-20', 'yyyy-mm-dd'), 2, 31, SYSDATE);
INSERT INTO Orders VALUES (3, 1296, 3269, to_date('2023-03-25', 'yyyy-mm-dd'), 1, 19, SYSDATE);
INSERT INTO Orders VALUES (4, 2394, 4129, to_date('2023-04-10', 'yyyy-mm-dd'), 4, 43, SYSDATE);
INSERT INTO Orders VALUES (5, 4008, 6194, to_date('2023-05-05', 'yyyy-mm-dd'), 2, 29, SYSDATE);
INSERT INTO Orders VALUES (6, 2394, 2569, to_date('2023-06-18', 'yyyy-mm-dd'), 3, 35, SYSDATE);
INSERT INTO Orders VALUES (7, 5297, 5015, to_date('2023-07-22', 'yyyy-mm-dd'), 1, 18, SYSDATE);
INSERT INTO Orders VALUES (8, 1296, 3269, to_date('2023-08-30', 'yyyy-mm-dd'), 2, 21, SYSDATE);
INSERT INTO Orders VALUES (9, 7856, 6194, to_date('2023-09-12', 'yyyy-mm-dd'), 3, 28, SYSDATE);
INSERT INTO Orders VALUES (10, 3129, 4129, to_date('2023-10-17', 'yyyy-mm-dd'), 2, 39, SYSDATE);
INSERT INTO Orders VALUES (11, 9364, 5015, to_date('2023-11-05', 'yyyy-mm-dd'), 4, 55, SYSDATE);
INSERT INTO Orders VALUES (12, 3129, 2569, to_date('2023-12-07', 'yyyy-mm-dd'), 1, 12, SYSDATE);
INSERT INTO Orders VALUES (13, 9364, 6194, to_date('2023-01-15', 'yyyy-mm-dd'), 3, 32, SYSDATE);
INSERT INTO Orders VALUES (14, 2394, 5015, to_date('2023-02-20', 'yyyy-mm-dd'), 2, 31, SYSDATE);
INSERT INTO Orders VALUES (15, 1027, 3269, to_date('2023-03-25', 'yyyy-mm-dd'), 1, 19, SYSDATE);

COMMIT;
```
#### Supplemental logging (Table level)

Supplemental logging at the table level ensures that all column changes associated with `INSERT`, `UPDATE` and `DELETE` operations are captured in the redo logs. To enable supplemental logging for the required tables, use the following commands.

```bash
ALTER TABLE Customers ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;
ALTER TABLE Products ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;
ALTER TABLE Orders ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;
```

## Deploying the Connector

1. Execute the Python script `create_debezium_connector_config.py` located in the `src` directory. This script will generate a JSON file named `debezium_connector.json`.

2. Copy the contents of `debezium_connector.json` and send a **POST** request to **Kafka Connect** service at `http://localhost:8083/connectors/`.

![Postman Screenshot](https://github.com/Karthik-Kishor/debezium-oracle/blob/Main/images/post-request.png)

3. If the above steps are done correctly, you should see the events in your Event Hubs Namespace. 

![Azure Screenshot](https://github.com/Karthik-Kishor/debezium-oracle/blob/Main/images/events.jpeg)

Note: In this scenario, `debezium_server` is the `database.server.name` specified in `debezium_connector.json`, and `customers` and `orders` are example tables in the database.

4. You can now use the SQL*Plus terminal where you created the initial test data to `INSERT`, `UPDATE`, or `DELETE` records within the `Customers`, `Orders` or `Products` table. You should see corresponding change events in Azure Event Hubs.

Run the `insert.py` located in the `src` directory to continuously insert data into the Oracle database.

## Environment Variables


| Name                 | Description                               |
| -------------------- | ----------------------------------------- |
| EH_NAME              | Name of the Event Hub Namespace           |
| EH_CONNECTION_STRING | Connection string of Shared access policy |
| HOST                 | Database host                             |
| PORT                 | Database port                             |
| PASSWORD             | Database password                         |
| SID                  | Name of the database                      |
| PDB                  | Name of the pluggable database            |
| LOGMINER_USER_NAME   | LogMiner user (in this case c##dbzuser)   |
| LOGMINER_PASSWORD    | LogMiner password (in this case c##dbz)   |
| DEBEZIUM_SERVER_NAME | Server name of your choice                |


## Appendix

#### Managing Debezium Connectors 

To view the current connectors, send a **GET** request to `http://localhost:8083/connectors/`. 

To remove a connector, send a **DELETE** request to `http://localhost:8083/connectors/{connector name}/`.
