import time
import json
import random
import argparse
import sys
import paho.mqtt.client as mqtt

parser = argparse.ArgumentParser()
parser.add_argument('--scenario', choices=['overload', 'normal'], default='normal')
args = parser.parse_args()

BROKER = "localhost"
PORT = 1883
USER = "sensor_user"
PASS = "SensPass567"
STATUS_TOPIC = "flat/corridor/system/status"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        # 1. Публікуємо статус системи з retain
        client.publish(STATUS_TOPIC, "online", qos=1, retain=True)
        # 2. Підписуємося на топіки команд актуаторів (Рівень сприйняття)
        client.subscribe("flat/room1/light/set", qos=1)
        client.subscribe("flat/room2/light/set", qos=1)
        client.subscribe("flat/corridor/heater/set", qos=1)
        print("[MQTT] Успішно підключено та авторизовано!")

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    ts = int(time.time())
    # Імітація роботи актуаторів: слухаємо /set -> відповідаємо в /state
    if msg.topic == "flat/room1/light/set":
        val = payload.get("state", 0)
        client.publish("flat/room1/light/state", json.dumps({"state": val, "ts": ts}), qos=1)
    elif msg.topic == "flat/room2/light/set":
        val = payload.get("state", 0)
        client.publish("flat/room2/light/state", json.dumps({"state": val, "ts": ts}), qos=1)
    elif msg.topic == "flat/corridor/heater/set":
        val = payload.get("state", "OFF")
        client.publish("flat/corridor/heater/state", json.dumps({"state": val, "ts": ts}), qos=1)

client = mqtt.Client()
client.username_pw_set(USER, PASS)
client.on_connect = on_connect
client.on_message = on_message

# НАЛАШТУВАННЯ LAST WILL AND TESTAMENT
client.will_set(STATUS_TOPIC, payload="offline", qos=1, retain=True)
client.connect(BROKER, PORT, 60)
client.loop_start()

cycle = 0
try:
    while True:
        ts = int(time.time())
        cycle += 1
        
        # Сценарій демонстрації перевантаження
        power = round(random.uniform(2550.0, 2700.0), 1) if args.scenario == 'overload' else round(random.uniform(300.0, 600.0), 1)
        
        # Публікація структурованої телеметрії (Вимога Т3)
        client.publish("flat/corridor/meter/telemetry", json.dumps({"power": power, "unit": "W", "ts": ts}), qos=1)
        client.publish("flat/corridor/climate/telemetry", json.dumps({"temperature": round(random.uniform(19.0, 22.0), 1), "humidity": round(random.uniform(40.0, 50.0), 1), "ts": ts}), qos=1)
        
        m1 = "ON" if random.random() > 0.5 else "OFF"
        lux1 = round(random.uniform(10.0, 30.0), 1) if m1 == "ON" else round(random.uniform(0.0, 10.0), 1)
        client.publish("flat/room1/motion/telemetry", json.dumps({"value": m1, "ts": ts}), qos=1)
        client.publish("flat/room1/illumination/telemetry", json.dumps({"lux": lux1, "ts": ts}), qos=1)
        
        m2 = "ON" if random.random() > 0.6 else "OFF"
        client.publish("flat/room2/motion/telemetry", json.dumps({"value": m2, "ts": ts}), qos=1)
        
        print(f"📡 Відправка: Потужність={power}W | Кімн1={m1} ({lux1}лк) | Кімн2={m2}")
        time.sleep(5)
except KeyboardInterrupt:
    client.publish(STATUS_TOPIC, "offline", qos=1, retain=True)
    client.loop_stop()
