import datetime
import json
import requests
import psycopg2
from flask import Flask, render_template, url_for, redirect

db_conf = {
    'host': 'covid-database',
    'port': 5432,
    'user': 'covidoved',
    'password': 'covidoved',
    'database': 'covidstats'
}


def get_raw_data(from_date, to_date):
    '''Get raw data from API'''
    session = requests.Session()
    try:
        response = session.get(
            'https://covidtrackerapi.bsg.ox.ac.uk/api/v2/stringency/date-range/'
            + from_date + '/' + to_date, timeout=15)
        resp_data = json.loads(response.text)
    except requests.exceptions.RequestException as exception:
        print(datetime.datetime.now().isoformat() + ' - ' + str(exception))
    finally:
        if session:
            session.close()
    return resp_data['data']


def create_table():
    '''Creating table for site'''
    try:

        db_conn = psycopg2.connect(**db_conf)
        cursor = db_conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS covid_stats;")
        cursor.execute('''CREATE TABLE covid_stats (
            id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            date_value DATE,
            country_code VARCHAR(3),
            confirmed INT,
            deaths INT,
            stringency_actual FLOAT(5),
            stringency FLOAT(5));''')
        db_conn.commit()
        cursor.close()
        db_conn.close()
    except psycopg2.Error as db_error:
        print("DB error: " + str(db_error))


def refresh_table():
    '''Processing the raw data, creating the covid_stats table and inserting data into it'''
    start = str(datetime.date(datetime.date.today().year, 1, 1))
    end = str(datetime.date.today())
    source_data = get_raw_data(start, end)
    result_data = []
    countries = ['RUS', 'USA', 'CHN', 'CAN',
                 'DEU', 'ITA', 'GBR', 'JPN', 'BRA', 'IND']
    for data in list(source_data.keys()):
        for contry in list(source_data[data].keys()):
            if contry in countries:
                result_data.append(
                    source_data[data][contry])
    try:
        db_conn = psycopg2.connect(**db_conf)
        cursor = db_conn.cursor()
        for result_data_line in result_data:
            cursor.execute('''INSERT INTO covid_stats (
                date_value,
                country_code,
                confirmed,
                deaths,
                stringency_actual,
                stringency)
                VALUES (%s, %s, %s, %s, %s, %s)''', (
                result_data_line['date_value'],
                result_data_line['country_code'],
                result_data_line['confirmed'],
                result_data_line['deaths'],
                result_data_line['stringency_actual'],
                result_data_line['stringency']))
        db_conn.commit()
        cursor.close()
        db_conn.close()
    except psycopg2.Error as db_error:
        print("DB error: " + str(db_error))


def get_data_from_db():
    '''Retrieve data from table covid_stats sorted by deaths in ascending order'''
    try:
        db_conn = psycopg2.connect(**db_conf)
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM covid_stats ORDER BY deaths ASC;")
        data = cursor.fetchall()
    except psycopg2.ProgrammingError:
        data = ()
    except psycopg2.Error as db_error:
        print("DB error: " + str(db_error))
    cursor.close()
    db_conn.close()
    return data


create_table()
refresh_table()

app = Flask(__name__)


@app.route('/')
def index():
    '''Define index route'''
    data = get_data_from_db()
    return render_template('index.html', data=data)


@app.route('/renew')
def renew():
    '''Define renew route'''
    refresh_table()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)