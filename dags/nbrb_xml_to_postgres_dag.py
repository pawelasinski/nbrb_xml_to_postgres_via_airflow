"""This DAG is for moving official exchange rates of the Belarusian ruble against foreign currencies
set by the National Bank of the Republic of Belarus on a daily basis from XML to Postgres.

"""

import os
import csv
import logging
from datetime import datetime
from xml.etree import ElementTree

import holidays
from psycopg2 import DataError, OperationalError

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.utils.edgemodifier import Label
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PATH_XML_DUMP = "/tmp/nbrb_rates.xml"
PATH_CSV_CONV = "/tmp/nbrb_rates.csv"
URL_NBRB_RATES_TEMPLATE = "https://services.nbrb.by/xmlexrates.aspx?ondate={{ ds }}"

DEFAULT_ARGS = {
    "start_date": days_ago(30),
    "owner": "pawelasinski",
    "doc_md": __doc__,
}

with DAG(
        dag_id="nbrb_xml_to_postgres_dag",
        default_args=DEFAULT_ARGS,
        tags=["asinski"],
        schedule_interval="@daily",
        max_active_runs=1,
        catchup=True,
) as dag:
    def is_business_day_func(execution_dt: str) -> bool:
        """Check if the given date is a business day (not a weekend and not a Belarusian national holiday)."""
        date_ = datetime.strptime(execution_dt, "%Y-%m-%d").date()
        belarus_holidays = holidays.BY(years=date_.year)
        if date_.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            logger.info("%s is a weekend day.", execution_dt)
            return False
        if date_ in belarus_holidays:
            logger.info("%s is a holiday: %s", execution_dt, belarus_holidays.get(date_))
            return False
        logger.info("%s is a business day.", execution_dt)
        return True


    is_business_day = ShortCircuitOperator(
        task_id="is_business_day",
        python_callable=is_business_day_func,
        op_kwargs={"execution_dt": "{{ ds }}"},
    )


    def does_data_exist_func(execution_date: str) -> bool:
        """Check if data for the given date already exists in the `nbrb_rates_daily_basis` table."""
        pg_hook = PostgresHook(postgres_conn_id="postgres_conn")
        with pg_hook.get_conn() as conn:
            with conn.cursor() as curs:
                query = "SELECT EXISTS (SELECT 1 FROM nbrb_rates_daily_basis WHERE date = %s)"
                curs.execute(query, (execution_date,))
                exists = curs.fetchone()[0]
        conn.close()
        if exists:
            logger.info("Data for %s already exists in the database.",
                        execution_date)
        else:
            logger.info("No data for %s found. Proceeding with the load.",
                        execution_date)
        return not exists


    does_data_exist = ShortCircuitOperator(
        task_id="does_data_exist",
        python_callable=does_data_exist_func,
        op_kwargs={"execution_date": "{{ ds }}"},
    )

    download_xml_nbrb_rates = BashOperator(
        task_id="download_xml_nbrb_rates",
        bash_command=f'curl "{URL_NBRB_RATES_TEMPLATE}" > {PATH_XML_DUMP}',
    )


    def convert_xml_to_csv_func() -> None:
        """Convert XML data to CSV format."""
        try:
            parser = ElementTree.XMLParser(encoding="utf-8")
            tree = ElementTree.parse(PATH_XML_DUMP, parser=parser)
            root = tree.getroot()
        except ElementTree.ParseError as e:
            logger.error("Error parsing XML: %s", e)
            raise

        with open(PATH_CSV_CONV, "w", encoding="utf-8") as f_csv:
            csv_writer = csv.writer(f_csv)
            for currency in root.findall("Currency"):
                try:
                    curr_id = currency.attrib.get("Id", "NA")
                    date_value = root.attrib.get("Date", "")
                    numcode = (currency.find("NumCode").text
                               if currency.find("NumCode") is not None else "")
                    charcode = (currency.find("CharCode").text
                                if currency.find("CharCode") is not None else "")
                    scale = (currency.find("Scale").text
                             if currency.find("Scale") is not None else "")
                    name = (currency.find("Name").text
                            if currency.find("Name") is not None else "")
                    rate = (currency.find("Rate").text
                            if currency.find("Rate") is not None else "")
                    row = [curr_id, date_value, numcode, charcode, scale, name, rate]
                    csv_writer.writerow(row)
                    logger.info(f"The row has been converted from XML to CSV: %s")
                except Exception as e:
                    logger.error("Error processing currency entry: %s", e)
                    continue


    convert_xml_to_csv = PythonOperator(
        task_id="convert_xml_to_csv",
        python_callable=convert_xml_to_csv_func,
    )


    def load_csv_into_postgres_func() -> None:
        """Load the CSV file into the `nbrb_rates_daily_basis` table in the Postgres database."""
        try:
            pg_hook = PostgresHook(postgres_conn_id="postgres_conn")
            with open(PATH_CSV_CONV, encoding="utf-8") as f_csv:
                sql_copy_query = 'COPY nbrb_rates_daily_basis FROM STDIN WITH (FORMAT csv, DELIMITER ",")'
                pg_hook.copy_expert(sql=sql_copy_query, filename=f_csv.name)
            logger.info("Data has been loaded successfully into the `exchange_rate_db` database.")
        except FileNotFoundError as e:
            logger.error("Error loading CSV file: %s", e)
            raise
        except OperationalError as e:
            logger.error("Error to connect to the `nbrb_rates_daily_basis` table: %s",
                         e)
            raise
        except DataError as e:
            logger.error("Data error occurred (possible schema mismatch): %s", e)
            raise
        except Exception as e:
            logger.exception("Error loading CSV into Postgres: %s", e)
            raise


    load_csv_into_postgres = PythonOperator(
        task_id="load_csv_into_postgres",
        python_callable=load_csv_into_postgres_func,
    )


    def delete_temp_files_func() -> None:
        """Delete temporary files created during the process."""
        for file_path in [PATH_XML_DUMP, PATH_CSV_CONV]:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info("%s has been deleted.", file_path)
                else:
                    logger.warning("%s has not been found for deletion.", file_path)
            except Exception as e:
                logger.exception("Error deleting %s: %s", file_path, e)


    delete_temp_files = PythonOperator(
        task_id="delete_temp_files",
        python_callable=delete_temp_files_func,
        trigger_rule="all_done",
    )

    is_business_day >> does_data_exist >> download_xml_nbrb_rates >> Label(
        "XML to CSV") >> convert_xml_to_csv >> Label("CSV to Postgres") >> load_csv_into_postgres >> delete_temp_files
