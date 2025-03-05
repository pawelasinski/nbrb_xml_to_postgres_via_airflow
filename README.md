# NBRB Exchange Rates Airflow DAG

This mini-project contains a simple Apache Airflow DAG that downloads daily exchange rates from the National Bank of the Republic of Belarus (NBRB) website in XML format and inserts the data into PostgreSQL database.

## Features

- The DAG downloads XML data with exchange rates from NBRB.
- The fetched data is inserted into the PostgreSQL table (`nbrb_rates_daily_basis`).
- Apache Airflow schedules and monitors the workflow.

## Prerequisites

- Docker
- Docker Compose

## Installation and Execution

### Step 0. Create and populate the `.env` file:

   ```env
   POSTGRES_DB=nbrb_db
   POSTGRES_USER=<username>
   POSTGRES_PASSWORD=<password>
   ```
Run the following command in terminal to export the variables:

   ```bash
   export $(grep -v '^#' .env | xargs)
   ```

### Step 1. Deploy Apache Airflow locally via Docker

Before setting up Postgres, you must deploy Airflow locally using Docker. Follow these steps:

1. Open a terminal and export your Airflow user ID:
   ```bash
   export AIRFLOW_UID=$(id -u)
   ```
2. Create a directory for Airflow and navigate into it:
   ```bash
   mkdir airflow_in_docker && cd $_
   ```
3. Download the official docker-compose file for Airflow (e.g. 2.10.0):
   ```bash
   curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.10.0/docker-compose.yaml'
   ```
4. Launch Airflow:
   ```bash
   docker compose up -d
   ```
   Airflow will be available at [http://localhost:8080](http://localhost:8080).
5. When you need to stop Airflow and remove volumes:
   ```bash
   docker compose down -v
   ```

Make sure that your custom DAG file (`nbrb_exchange_rates_dag.py`) is placed **in the `dags` directory of the deployed Airflow instance** (see the [Project File Structure](#project-file-structure)) so that Airflow can detect it. After this step, Airflow will automatically detect the DAG.

### Step 2. Deploy Postgres the same way

Once Airflow is up and running, set up Postgres to store the exchange rates data.

#### 2.1 Build and run the Postgres container

Go to the `nbrb_db` directory and execute the following commands:

   ```bash
   cd nbrb_db
   docker build -t nbrb_postgres .
   docker volume create nbrb_postgres_vol
   docker run -d \
     -v nbrb_postgres_vol:/var/lib/postgresql/data \
     -e POSTGRES_DB=$POSTGRES_DB \
     -e POSTGRES_USER=$POSTGRES_USER \
     -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
     --name nbrb_postgres \
     -p 5432:5432 \
     nbrb_postgres
   ```

#### 2.2 Verify the table creation

Check that the table `nbrb_rates_daily_basis` was created successfully using one of these commands:

   ```bash
   docker exec -it asinski_postgres_cont psql -U $POSTGRES_USER -d $POSTGRES_DB -W -c "SELECT * FROM nbrb_rates_daily_basis;"
   docker exec -it asinski_postgres_cont psql -U $POSTGRES_USER -d $POSTGRES_DB -W -c "\d nbrb_rates_daily_basis"
   ```

#### 2.3 Connect Postgres to the Airflow network

To allow Airflow to interact with Postgres, connect the Postgres container to the corresponding Airflow network:

   ```bash
   docker network connect airflow_in_docker_default nbrb_postgres
   ```

### Step 3. Create an Airflow connection to the Postgres container

Inside the Airflow webserver container, add a new connection for Postgres so that the DAG can use it.

1. Open a bash session in the Airflow webserver container:
   ```bash
   docker exec -it airflow_in_docker-airflow-webserver-1 bash
   ```
2. Add the connection:
   ```bash
   airflow connections add 'postgres_conn' \
     --conn-type 'postgres' \
     --conn-host 'nbrb_postgres' \
     --conn-schema 'nbrb_db' \
     --conn-login '<username>' \
     --conn-password '<password>' \
     --conn-port '5432'
   ```

### Step 4. Run the DAG via Airflow UI

## Project File Structure

```text
nbrb_xml_to_postgres_via_airflow/
├── dags/                                  # Directory for custom Airflow DAG
│   └── nbrb_exchange_rates_dag.py           # Custom Airflow DAG
├── nbrb_db/                               # Postgres related files
│   ├── Dockerfile                           # Dockerfile for the custom Postgres image
│   └── init_db.sh                           # Script to create the `nbrb_rates_daily_basis` table
├── airflow_in_docker/                     # Airflow deployment directory (includes docker-compose.yaml)
│   ├── ...                                  # Other Airflow configuration directories and files
│   ├── dags/                                # The DAGs that runs on Airflow
│   └── ...                                  # Other Airflow configuration directories and files
├── .env                                   # Environment variables for credentials and URLs
├── .gitignore                             # Git ignore file
├── LICENSE                                # Project license
└── README.md                              # Project description
```

## Possible Extensions

- Set up notifications (email/Slack) for DAG failures.

## License

[MIT License](./LICENSE)

## Author

Pawel Asinski (pawel.asinski@gmail.com)
