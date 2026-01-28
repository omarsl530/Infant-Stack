import paho.mqtt.client as mqtt
import psycopg2
import json
import datetime

# --- CONFIGURATION ---
MQTT_BROKER = "localhost"  # Since this runs in WSL and Docker ports are mapped to localhost
MQTT_PORT = 1883
MQTT_TOPIC = "hospital/+/movements"  # Wildcard: listens to all zones (e.g., hospital/gate1/movements)

DB_HOST = "localhost"
DB_NAME = "biobaby_db"
DB_USER = "admin"
DB_PASS = "securepassword"

# --- DATABASE CONNECTION ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

# --- MQTT CALLBACKS ---

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Connected to MQTT Broker! Listening on {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        # 1. Decode the payload
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        print(f"📩 Received: {data}")

        # 2. Extract key fields
        tag_id = data.get("tag_id")
        reader_id = data.get("reader_id")
        event_type = data.get("event")
        meta = json.dumps(data.get("meta", {})) # Convert extra data to JSON string

        # 3. Insert into PostgreSQL
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            query = """
                INSERT INTO movement_logs (tag_id, reader_id, event_type, metadata)
                VALUES (%s, %s, %s, %s)
            """
            cur.execute(query, (tag_id, reader_id, event_type, meta))
            conn.commit()
            cur.close()
            conn.close()
            print("💾 Saved to Database.")
            
    except Exception as e:
        print(f"⚠️ Error processing message: {e}")

# --- MAIN LOOP ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("⏳ Connecting to Broker...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
client.loop_forever()