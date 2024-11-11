1. ```bash
   cd docker_postgres
   docker build -t asinski_postgres_img .
   docker volume create asinski_postgres_vol
   docker run -d --rm -v asinski_postgres_vol:/var/lib/postgresql/data -e POSTGRES_PASSWORD=admin -e POSTGRES_USER=admin -e POSTGRES_DB=asinski_postgres_db --name asinski_postgres_cont -p 5432:5432 asinski_postgres_img
   docker exec -it asinski_postgres_cont psql -U admin -d asinski_postgres_db -W -c "SELECT * FROM nbrb_rates_daily_basis;"
   docker exec -it asinski_postgres_cont psql -U admin -d asinski_postgres_db -W -c "\d nbrb_rates_daily_basis"
   docker exec -it asinski_postgres_cont psql -U admin -d asinski_postgres_db -W -c "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'nbrb_rates_daily_basis');"  # Подходит, когда нужно использовать стандартизированный подход, совместимый с различными базами данных. Это удобный вариант, когда в будущем планируется миграция на другие СУБД или нужно работать в контексте различных типов баз данных.
   docker exec -it asinski_postgres_cont psql -U admin -d asinski_postgres_db -W -c "SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_tables WHERE schemaname = 'public' AND tablename = 'nbrb_rates_daily_basis');"  # Рекомендуется использовать, если требуется глубокий доступ к специфичным возможностям PostgreSQL, так как таблицы в pg_catalog содержат больше информации, которая может быть полезной при работе с PostgreSQL.
   ```
2. ```bash
   docker network connect airflow_in_docker_default asinski_postgres_cont
   ``` 
3. ```bash
   docker exec -it airflow_in_docker-airflow-webserver-1 bash
   airflow connections add 'asinski_postgres_conn' \
    --conn-type 'postgres' \
    --conn-host 'asinski_postgres_cont' \
    --conn-schema 'asinski_postgres_db' \
    --conn-login 'admin' \
    --conn-password 'admin' \
    --conn-port '5432'
    ```
