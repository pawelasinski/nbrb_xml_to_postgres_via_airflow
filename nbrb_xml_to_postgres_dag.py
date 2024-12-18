"""This DAG is for moving official exchange rates of the Belarusian ruble against foreign currencies
set by the National Bank of the Republic of Belarus on a daily basis from XML to Postgres.

Todo:
    * Make possible to extract the rates only for business days, i.e. excepting weekends and holiday national days. You need to twick schedule_interval, or implement BranchOperator or ShortCircuitOperator.

"""
import os
import csv
import logging
from datetime import datetime
from xml.etree import ElementTree

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.utils.edgemodifier import Label
from airflow.operators.bash import BashOperator
from airflow.operators.python_operator import PythonOperator, ShortCircuitOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

path_xml_dump = '/tmp/nbrb_rates.xml'
path_csv_conv = '/tmp/nbrb_rates.csv'
url_nbrb_rates = 'https://services.nbrb.by/xmlexrates.aspx?ondate={{ ds }}'

DEFAULT_ARGS = {
    'start_date': days_ago(30),
    'owner': 'pawelasinski',
    'doc_md': __doc__,
}

with DAG(
        dag_id='nbrb_xml_to_postgres_dag',
        default_args=DEFAULT_ARGS,
        tags=['tutorial'],
        schedule_interval='0 0 * * 1-6',
        max_active_runs=1,
):
    def is_weekday_func(execution_dt):
        return datetime.strptime(execution_dt, '%Y-%m-%d').weekday() in range(0, 5)


    is_weekday = ShortCircuitOperator(
        task_id='is_weekday',
        python_callable=is_weekday_func,
        op_kwargs={'execution_dt': '{{ ds }}'}
    )


    def check_if_data_exists_func(execution_date):
        pg_hook = PostgresHook(postgres_conn_id='asinski_postgres_conn')

        with pg_hook.get_conn() as conn:
            cursor = conn.cursor()

            query = 'SELECT EXISTS (SELECT 1 FROM nbrb_rates_daily_basis WHERE date = %s)'
            cursor.execute(query, (execution_date,))
            exists = cursor.fetchone()[0]

            cursor.close()

        return not exists


    check_if_data_exists = ShortCircuitOperator(
        task_id='check_if_data_exists',
        python_callable=check_if_data_exists_func,
        op_kwargs={'execution_date': '{{ ds }}'},
    )

    download_xml_nbrb_rates = BashOperator(
        task_id='download_xml_nbrb_rates',
        bash_command=f'curl "{url_nbrb_rates}" > {path_xml_dump}'
    )


    def convert_xml_to_csv_func():
        parser = ElementTree.XMLParser(encoding='utf-8')
        tree = ElementTree.parse(f'{path_xml_dump}', parser=parser)
        root = tree.getroot()

        with open(f'{path_csv_conv}', 'w') as csv_file:
            csv_writer = csv.writer(csv_file)
            for currency in root.findall('Currency'):
                numcode = currency.find('NumCode').text
                charcode = currency.find('CharCode').text
                scale = currency.find('Scale').text
                name = currency.find('Name').text
                rate = currency.find('Rate').text

                the_whole_curr_row = [
                    currency.attrib['Id'], root.attrib['Date'],
                    numcode, charcode, scale, name, rate
                ]
                csv_writer.writerow(the_whole_curr_row)

                logging.info(the_whole_curr_row)


    convert_xml_to_csv = PythonOperator(
        task_id='convert_xml_to_csv',
        python_callable=convert_xml_to_csv_func,
    )


    def load_csv_into_postgres_func():
        pg_hook = PostgresHook(postgres_conn_id='asinski_postgres_conn')

        with open(f'{path_csv_conv}', 'r') as csv_file:
            pg_hook.copy_expert(sql="COPY nbrb_rates_daily_basis FROM stdin DELIMITER ','",
                                filename=csv_file.name)


    load_csv_into_postgres = PythonOperator(
        task_id='load_csv_into_postgres',
        python_callable=load_csv_into_postgres_func,
    )


    def delete_temp_files_func():
        os.remove(path_xml_dump)
        os.remove(path_csv_conv)


    delete_temp_files = PythonOperator(
        task_id='delete_temp_files',
        python_callable=delete_temp_files_func,
        trigger_rule='all_done'
    )

    is_weekday >> check_if_data_exists >> download_xml_nbrb_rates >> Label("XML to CSV") >> convert_xml_to_csv >> Label(
        "CSV to Postgres") >> load_csv_into_postgres >> delete_temp_files
