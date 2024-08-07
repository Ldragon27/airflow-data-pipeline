FROM apache/airflow:2.9.2

CMD ["/bin/bash"]

RUN pip install pymssql \
    && pip install pyodbc\
    && pip install apache-airflow-providers-common-sql\
    && pip install apache-airflow-providers-oracle\
    && pip install apache-airflow-providers-microsoft-mssql\
    && pip install apache-airflow-providers-microsoft-mssql[odbc]\
    && pip install apache-airflow-providers-odbc\
    && pip install pandas\
    && pip install gitpython

USER root
RUN apt-get update
RUN apt-get install sudo
RUN sudo apt-get install -y git

USER airflow