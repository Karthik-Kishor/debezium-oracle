import oracledb
import os
import datetime
import time
from faker import Faker
from dotenv import load_dotenv
import random
from apscheduler.schedulers.blocking import BlockingScheduler
from colorama import Fore

load_dotenv()

user_name = os.getenv("LOGMINER_USER_NAME")
password = os.getenv("LOGMINER_PASSWORD")
host = "localhost" or os.getenv("HOST")
port = os.getenv("PORT")
pdb = os.getenv("PDB")

random_range_start = 10000
random_range_end = 1000000
fake = Faker()


class InsertData:
    def __init__(self, user_name, password, host, port, database, num_records=10):
        self.user_name = user_name
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.num_records = num_records

    def get_connection(self):
        conn_string = f"{self.host}:{self.port}/{self.database}"
        self.connection = oracledb.connect(
            user=self.user_name, password=self.password, dsn=conn_string
        )

    def get_products_and_customers(self):
        p_list = []
        c_list = []

        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM products")
            rows = cursor.fetchall()
            for r in rows:
                p_list.append((r[0], r[2]))

        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM customers SAMPLE(20) WHERE ROWNUM <= 20")
            rows = cursor.fetchall()
            for r in rows:
                c_list.append(r[0])
        return p_list, c_list

    def generate_orders(self):
        o_data = []
        products_list, customers_list = self.get_products_and_customers()
        for _ in range(self.num_records):
            customer_id = fake.random_element(customers_list)
            product_id, product_price = fake.random_element(products_list)
            order_id = (
                customer_id
                + product_id
                + random.randint(random_range_start, random_range_end)
            )
            date = datetime.datetime.now()
            quantity = fake.random_digit_not_null()
            total_amount = quantity * product_price
            o_data.append(
                (
                    order_id,
                    product_id,
                    customer_id,
                    date,
                    quantity,
                    total_amount,
                    date,
                )
            )
        return o_data

    def generate_customer_data(self):
        c_data = []
        email_list = [
            "gmail.com",
            "outlook.com",
            "hotmail.com",
            "proton.me",
            "protonmail.com",
            "yahoo.com",
            "icloud.com",
            "aol.com",
            "tutamail.com",
            "tuta.io",
            "tuta.com",
            "yandex.com",
            "example.com",
        ]
        separator = ["", "-", "_", ".", "--", "__"]
        for _ in range(self.num_records):
            customer_id = int(time.time()) + random.randint(
                random_range_start, random_range_end
            )
            first_name = fake.first_name()
            last_name = fake.last_name()
            email_provider = fake.random_element(email_list)
            email_separator = fake.random_element(separator)
            email = (
                first_name.lower()
                + email_separator
                + last_name.lower()
                + "@"
                + email_provider
            )
            modified_date = datetime.datetime.now()
            c_data.append((customer_id, first_name, last_name, email, modified_date))
        return c_data

    def insert_into_orders(self):
        try:
            orders_data = self.generate_orders()
            with self.connection.cursor() as cursor:
                sql = "INSERT INTO orders (order_id, product_id, customer_id, order_date, quantity, total_amount, modified_date) values (:order_id, :product_id, :customer_id, :order_date, :quantity, :total_amount, :modified_date)"
                cursor.executemany(sql, orders_data)
                self.connection.commit()
            print(
                Fore.GREEN
                + f"Successfully inserted {self.num_records} records into orders table"
            )
        except Exception as e:
            print(Fore.RED + f"{e}")
            self.get_connection()
            self.insert_into_orders()

    def insert_into_customers(self):
        try:
            customer_data = self.generate_customer_data()
            with self.connection.cursor() as cursor:
                sql = "INSERT INTO customers (customer_id, first_name, last_name, email, modified_date) values (:customer_id, :first_name, :last_name, :email, :modified_date)"
                cursor.executemany(sql, customer_data)
                self.connection.commit()
            print(
                Fore.BLUE
                + f"Successfully inserted {self.num_records} records into customers table"
            )
        except Exception as e:
            print(Fore.RED + f"{e}")
            self.get_connection()
            self.insert_into_customers()


if __name__ == "__main__":
    ins = InsertData(user_name, password, host, port, pdb, num_records=2)

    ins.get_connection()

    scheduler = BlockingScheduler(daemon=False)
    scheduler.add_job(ins.insert_into_customers, trigger="interval", seconds=10)
    scheduler.add_job(ins.insert_into_orders, trigger="interval", seconds=15)
    scheduler.start()
