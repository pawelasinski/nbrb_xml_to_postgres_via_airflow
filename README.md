This is a simple Apache Airflow DAG that downloads the daily exchange rates from the National Bank of the Republic of Belarus (NBRB) website in XML format and inserts them into a PostgreSQL database.

#### Prerequisites
1. The following commands are to initialize the PostgreSQL database:
    ```bash
    cd docker_postgres
    docker build -t asinski_postgres_img .
    docker volume create asinski_postgres_vol
    docker run -d -v asinski_postgres_vol:/var/lib/postgresql/data -e POSTGRES_PASSWORD=admin -e POSTGRES_USER=admin -e POSTGRES_DB=asinski_postgres_db --name asinski_postgres_cont -p 5432:5432 asinski_postgres_img
    ```
    and check that the table has been created successfully (it is allowed to use any of the following commands):
    ```bash
    docker exec -it asinski_postgres_cont psql -U admin -d asinski_postgres_db -W -c "SELECT * FROM nbrb_rates_daily_basis;"
    docker exec -it asinski_postgres_cont psql -U admin -d asinski_postgres_db -W -c "\d nbrb_rates_daily_basis"
    docker exec -it asinski_postgres_cont psql -U admin -d asinski_postgres_db -W -c "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'nbrb_rates_daily_basis');"
    docker exec -it asinski_postgres_cont psql -U admin -d asinski_postgres_db -W -c "SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_tables WHERE schemaname = 'public' AND tablename = 'nbrb_rates_daily_basis');"
    ```
2. Then, it's needed to connect the PostgreSQL container to the Airflow network:
    ```bash
   docker network connect airflow_in_docker_default asinski_postgres_cont
   ``` 
3. At last, it's needed to create a new connection entity in Airflow: 
   ```bash
   docker exec -it airflow_in_docker-airflow-webserver-1 bash
   airflow connections add 'asinski_postgres_conn' \
    --conn-type 'postgres' \
    --conn-host 'asinski_postgres_cont' \
    --conn-schema 'asinski_postgres_db' \
    --conn-login 'admin' \  # Do not expose credentials in a real-world production scenario.
    --conn-password 'admin' \  # Do not expose credentials in a real-world production scenario.
    --conn-port '5432'
    ```
