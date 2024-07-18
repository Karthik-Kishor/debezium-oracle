import json
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


EH_NAME = os.getenv("EH_NAME")
EH_CONNECTION_STRING = os.getenv("EH_CONNECTION_STRING")

HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
USER_NAME = os.getenv("LOGMINER_USER_NAME")
PASSWORD = os.getenv("LOGMINER_PASSWORD")

SID = os.getenv("SID")
PDB = os.getenv("PDB")

DEBEZIUM_SERVER_NAME = os.getenv("DEBEZIUM_SERVER_NAME")


with open(os.path.join("src", "connector.json"), "r") as f:
    connector_json = json.load(f)


connector_json["name"] = "oracle_connector" + "_" + datetime.now().strftime("%Y-%m-%d")

connector_json["config"]["database.hostname"] = HOST
connector_json["config"]["database.port"] = PORT
connector_json["config"]["database.user"] = USER_NAME
connector_json["config"]["database.password"] = PASSWORD
connector_json["config"]["database.dbname"] = SID
connector_json["config"]["database.pdb.name"] = PDB
connector_json["config"]["database.server.name"] = DEBEZIUM_SERVER_NAME

connector_json["config"]["database.history.kafka.bootstrap.servers"] = f"{EH_NAME}.servicebus.windows.net:9093"
connector_json["config"]["database.history.sasl.jaas.config"] = f"org.apache.kafka.common.security.plain.PlainLoginModule required username=\"$ConnectionString\" password=\"{EH_CONNECTION_STRING}\";"

connector_json["config"]["database.history.producer.bootstrap.servers"] = f"{EH_NAME}.servicebus.windows.net:9093"
connector_json["config"]["database.history.producer.sasl.jaas.config"] = f"org.apache.kafka.common.security.plain.PlainLoginModule required username=\"$ConnectionString\" password=\"{EH_CONNECTION_STRING}\";"

connector_json["config"]["database.history.consumer.bootstrap.servers"] = f"{EH_NAME}.servicebus.windows.net:9093"
connector_json["config"]["database.history.consumer.sasl.jaas.config"] = f"org.apache.kafka.common.security.plain.PlainLoginModule required username=\"$ConnectionString\" password=\"{EH_CONNECTION_STRING}\";"


with open(os.path.join("src", "debezium_connector.json"), "w") as f:
    json.dump(connector_json, f, indent=4)
