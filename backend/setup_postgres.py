import os
from pathlib import Path

import psycopg2
from dotenv import dotenv_values
from psycopg2 import sql


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    config = dotenv_values(PROJECT_ROOT / '.env')
    database = config.get('DB_NAME') or 'santana_afiliados_db'
    username = config.get('DB_USER') or 'santana_admin'
    password = config.get('DB_PASSWORD')
    if not password or password == 'replace-with-your-database-password':
        raise SystemExit('Set a database password in the project .env file before setup.')

    connection = psycopg2.connect(
        dbname='postgres',
        user=os.getenv('PG_SUPERUSER', 'postgres'),
        host='127.0.0.1',
        port=config.get('DB_PORT') or '5432',
    )
    connection.autocommit = True

    with connection, connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (username,))
        role_exists = cursor.fetchone() is not None
        role_statement = sql.SQL('ALTER ROLE {} WITH LOGIN PASSWORD %s' if role_exists else 'CREATE ROLE {} WITH LOGIN PASSWORD %s')
        cursor.execute(role_statement.format(sql.Identifier(username)), (password,))

        cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (database,))
        if cursor.fetchone() is None:
            cursor.execute(
                sql.SQL('CREATE DATABASE {} OWNER {}').format(
                    sql.Identifier(database),
                    sql.Identifier(username),
                )
            )
        else:
            cursor.execute(
                sql.SQL('GRANT ALL PRIVILEGES ON DATABASE {} TO {}').format(
                    sql.Identifier(database),
                    sql.Identifier(username),
                )
            )

    connection.close()
    print(f'Database user and database are ready: {username}/{database}')


if __name__ == '__main__':
    main()
