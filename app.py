from datetime import datetime

import MySQLdb.cursors
import pandas as pd
from flask import Flask, render_template, request, redirect, flash, url_for
from flask_login import LoginManager, UserMixin, login_required
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash

import forecast

app = Flask(__name__)

app.secret_key = 'secret key1111'

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'mysqlpassword1092_'
app.config['MYSQL_DB'] = 'systemDatabase'

mysql = MySQL(app)
manager = LoginManager(app)
manager.init_app(app)


class Account(UserMixin):
    def __init__(self, id, username, password, role_id, active=True):
        self.id = id
        self.username = username
        self.password = password
        self.role_id = role_id
        self.active = active


@manager.user_loader
def load_user(account_id):
    for account in accounts:
        if account.get_id() == account_id:
            return account


class Commodity:

    def __init__(self, name):
        self.name = name
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM commodities WHERE commodity_name = % s', [str(name)])
        self.id = cursor.fetchone()['id']
        cursor.execute('SELECT price_setting_date, price FROM prices WHERE fk_commodity_prices = % s', [self.id])
        self.prices = pd.DataFrame(cursor.fetchall())
        self.forecaster = forecast.Forecaster(self.prices, timestep=40)
        self.predictions = []
        now = datetime.now().date()
        last_date = self.prices.iloc[-1:, 0].values[0]
        if last_date < datetime(year=now.year, month=now.month, day=1).date():
            delta = (now - last_date)
            delta = 2
            self.prices = pd.concat(
                [self.prices, pd.DataFrame(self.forecaster.predict(delta),
                                           columns=['price_setting_date', 'price'])],
                ignore_index=True)
            self.forecaster.update(self.prices)

    def predict(self, period):
        self.predictions = self.forecaster.predict(period)

    def get_name(self):
        return self.name

    def get_prices(self):
        return self.prices

    def get_predictions(self):
        return self.predictions


commodity_list = []
accounts = []


@app.route('/')
def index():
    # addFromCsv('datasets/bananas.csv')
    # addFromCsv('datasets/cocoa_beans.csv')
    # addFromCsv('datasets/cotton.csv')
    # addFromCsv('datasets/maize.csv')
    # addFromCsv('datasets/oranges.csv')
    # addFromCsv('datasets/peanuts.csv')
    # addFromCsv('datasets/rice.csv')
    # addFromCsv('datasets/soybeans.csv')
    # addFromCsv('datasets/tea.csv')
    # addFromCsv('datasets/wheat.csv')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM commodities')
    commodities = cursor.fetchall()
    names = [row['commodity_name'] for row in commodities]
    if not commodity_list:
        for name in names:
            commodity_list.append(Commodity(name))

    topThreeWinners, topThreeLosers = TopThreeWinnersAndLosers(commodity_list)
    context = {
        "top5": topThreeWinners,
        "bottom5": topThreeLosers,
        "names": names,
        "commodity_list": commodity_list
    }
    return render_template('index.html', context=context)


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM accounts')
    for row in cursor:
        accounts.append(Account(row['id'], row['username'], row['pass'], row['role_id']))

    login = request.form.get('username')
    password = request.form.get('password')

    if login and password:
        for account in accounts:
            if account.username == login:
                if check_password_hash(account.password, password):
                    next_page = request.args.get('next')

                    return redirect(next_page)
                else:
                    flash('Login or password is not correct')
    else:
        flash('Please fill login and password fields')

    return render_template('login.html')


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('login_page') + '?next=' + request.url)

    return response


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    login = request.form.get('username')
    password = request.form.get('password')
    repeat_password = request.form.get('repeat_password')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM roles WHERE role_name = % s', ['user'])

    role_id = cursor.fetchone()['id']

    if request.method == 'POST':
        if not (login or password or repeat_password):
            flash('Please, fill all fields!')
        elif password != repeat_password:
            flash('Passwords are not equal!')
        else:
            hash_pwd = generate_password_hash(password)
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO accounts VALUES (NULL, % s, % s, % s)', [login, hash_pwd, role_id])
            mysql.connection.commit()

            return redirect(url_for('login_page'))

    return render_template('register.html')


@app.route('/commodity/<name>', methods=['GET', 'POST'])
@login_required
def crop_profile(name):
    select = request.form.get('forecast_period')

    if select is not None:
        select = int(select)

    else:
        select = 12

    commodity = None
    for item in commodity_list:
        if item.get_name() == name:
            commodity = item

    commodity.predict(select)

    forecast_crop_values = commodity.get_predictions()
    prev_crop_values = commodity.get_prices().iloc[-12:, :].values.tolist()
    forecast_list = []
    i = 0
    for value in forecast_crop_values:
        if i == 0:
            forecast_list.append((value[0], round(value[1], 2),
                                  round(((value[1] - prev_crop_values[-1][1]) / prev_crop_values[-1][1]) * 100, 2)))

        else:
            forecast_list.append((value[0], round(value[1], 2), round(
                ((value[1] - forecast_crop_values[i - 1][1]) / forecast_crop_values[i - 1][1]) * 100, 2)))

        i = i + 1
    forecast_crop_values = forecast_list
    max_crop = []
    min_crop = []
    if forecast_crop_values:
        minimum = min(forecast_crop_values, key=lambda x: x[1])
        maximum = max(forecast_crop_values, key=lambda x: x[1])
        min_crop = [minimum[0].strftime("%B %Y"), round(float(minimum[1]), 2)]
        max_crop = [maximum[0].strftime("%B %Y"), round(float(maximum[1]), 2)]

    forecast_x = [i[0].strftime("%B %Y") for i in forecast_crop_values]
    forecast_y = [i[1] for i in forecast_crop_values]
    previous_x = [i[0].strftime("%B %Y") for i in prev_crop_values]
    previous_y = [float(i[1]) for i in prev_crop_values]
    current_price = round(previous_y[-1], 2)
    crop_data = ['', '', '', '']
    context = {
        "name": name,
        "max_crop": max_crop,
        "min_crop": min_crop,
        "forecast_values": forecast_crop_values,
        "forecast_x": str(forecast_x),
        "forecast_y": forecast_y,
        "previous_values": prev_crop_values,
        "previous_x": previous_x,
        "previous_y": previous_y,
        "current_price": current_price,
        "image_url": crop_data[0],
        "prime_loc": crop_data[1],
        "type_c": crop_data[2],
        "export": crop_data[3]
    }
    return render_template('commodity.html', context=context)


def addCommodity(name):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM commodities WHERE commodity_name = % s', [name])
    if not bool(cursor.fetchone()):
        cursor.execute('INSERT INTO commodities VALUES (NULL, % s)', [name])
        mysql.connection.commit()


def addPrice(name, date, price):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM commodities WHERE commodity_name = % s', [name])
    name_id = cursor.fetchone()['id']
    cursor.execute('INSERT INTO prices VALUES (NULL, % s, % s, % s)', [date, price, name_id])
    mysql.connection.commit()


def addFromCsv(filename):
    df = pd.read_csv(filename).values
    addCommodity(df[0][3])
    for row in df:
        addPrice(row[3], row[0], row[1])


def TopThreeWinnersAndLosers(commodity_list):
    for commodity in commodity_list:
        commodity.predict(1)

    table = []
    for commodity in commodity_list:
        table.append((commodity, commodity.get_predictions()[0][1],
                      ((commodity.get_predictions()[0][1] - commodity.get_prices().iloc[-1, 1]) /
                       commodity.get_predictions()[0][1]) * 100))

    table.sort(key=lambda x: x[2], reverse=True)

    to_send_winners = []
    for item in table:
        if len(to_send_winners) > 2:
            break
        if item[2] < 0:
            break
        if item[2] > 0:
            to_send_winners.append((item[0].get_name().capitalize(), round(item[1], 2), round(item[2], 2)))

    table.sort(key=lambda x: x[2])

    to_send_losers = []
    for item in table:
        if len(to_send_losers) > 2:
            break
        if item[2] > 0:
            break
        if item[2] < 0:
            to_send_losers.append((item[0].get_name().capitalize(), round(item[1], 2), round(item[2], 2)))

    return to_send_winners, to_send_losers


if __name__ == "__main__":
    app.run()
