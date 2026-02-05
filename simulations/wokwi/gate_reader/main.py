import network
import time
import ujson
from machine import Pin
import sys

sys.path.append('/common')
from common.config import cfg
from common.mqtt_client import RobustMQTTClient
from common.security import Security
from common.utils import log

# --- Hardware Setup ---
# Buttons simulate detecting specific tags at the gate
BTN_IT1_PIN = 13  # Simulate IT-0001
BTN_IT2_PIN = 12  # Simulate IT-0002 (e.g. Unpaired/Lost)

LED_AUTH_PIN = 2  # Green (Onboard) - Authorized
LED_DENY_PIN = 4  # Red - Denied/Alarm

btn_it1 = Pin(BTN_IT1_PIN, Pin.IN, Pin.PULL_UP)
btn_it2 = Pin(BTN_IT2_PIN, Pin.IN, Pin.PULL_UP)
led_auth = Pin(LED_AUTH_PIN, Pin.OUT)
led_deny = Pin(LED_DENY_PIN, Pin.OUT)

# --- State ---
device_id = cfg.get("GATE_ID")
if device_id == "GATE-1": 
    # Config might return GATE-1 as default, but let's allow overwrite 
    # or just use DEVICE_ID if set.
    pass

secret_key = cfg.get("SECRET_KEY")
security = Security(secret_key)
mqtt_client = None

# Cache: { "ID": { "ts": timestamp, "data": msg_payload } }
presence_cache = {}
PRESENCE_WINDOW = cfg.get("PRESENCE_EXPIRY") # e.g. 30s

# --- Helpers ---

def connect_wifi():
    ssid = cfg.get("WIFI_SSID")
    password = cfg.get("WIFI_PASS")
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        log(device_id, "Connecting to network...")
        sta_if.active(True)
        sta_if.connect(ssid, password)
        while not sta_if.isconnected():
            time.sleep(0.1)
    log(device_id, f"Network connected: {sta_if.ifconfig()}")

def handle_presence(topic, msg):
    try:
        data = ujson.loads(msg)
        if security.verify_signature(data):
            # Store in cache
            sender_id = data.get("id")
            if sender_id:
                presence_cache[sender_id] = {
                    "ts": time.time(),
                    "data": data
                }
                # log(device_id, f"Seen {sender_id}")
    except Exception as e:
        log(device_id, f"Error parsing presence: {e}", "ERROR")

def check_gate_logic(infant_id):
    log(device_id, f"Processing Gate Passage for {infant_id}...")
    
    # 1. Look up Infant in Cache to find Mother ID
    infant_record = presence_cache.get(infant_id)
    
    # For simulation purposes, if infant not in cache but we "scanned" it via button,
    # we assume it's here but maybe hasn't published status recently.
    # We need the mother_id though.
    # If not in cache, we can't verify pairing -> Deny (fail safe).
    
    authorized = False
    mother_id = None
    fail_reason = "Infant unknown"
    
    if infant_record:
        # Check freshness of infant data ? 
        # Actually, the button press implies physical presence NOW.
        # So we just use the cached mother_id.
        mother_id = infant_record["data"].get("mother_id")
        
        if mother_id:
            # 2. Check if Mother is in Cache and Fresh
            mother_record = presence_cache.get(mother_id)
            if mother_record:
                age = time.time() - mother_record["ts"]
                if age < PRESENCE_WINDOW:
                    authorized = True
                    fail_reason = None
                    log(device_id, f"Authorized! Mother {mother_id} is present ({int(age)}s ago).")
                else:
                    fail_reason = f"Mother {mother_id} away ({int(age)}s)"
            else:
                fail_reason = f"Mother {mother_id} not seen"
        else:
            fail_reason = "No pairing data for Infant"
    else:
        log(device_id, "Infant not in presence cache (wait for broadcast)", "WARN")
        # In a real system, we might trigger a scan request.
    
    # Publish Gate Event
    event = {
        "type": "gate_pass",
        "gate_id": device_id,
        "infant_id": infant_id,
        "mother_id": mother_id,
        "authorized": authorized,
        "reason": fail_reason 
    }
    
    topic = f"security/gate/{device_id}/events"
    mqtt_client.publish(topic, security.sign_message(event))
    
    # Local IO Feedback
    if authorized:
        led_auth.value(1)
        led_deny.value(0)
        time.sleep(2)
        led_auth.value(0)
    else:
        led_auth.value(0)
        led_deny.value(1)
        # Also Raise Alarm if Denied?
        # "If not authorized and infant present, raise an alarm."
        log(device_id, f"ALARM! Unauthorized exit attempt: {fail_reason}", "ALERT")
        alarm_msg = {
            "type": "alarm",
            "code": "UNAUTHORIZED_EXIT",
            "infant_id": infant_id,
            "gate_id": device_id
        }
        mqtt_client.publish(f"security/alerts/{device_id}", security.sign_message(alarm_msg))
        
        for _ in range(5):
            led_deny.value(0)
            time.sleep(0.1)
            led_deny.value(1)
            time.sleep(0.1)
        led_deny.value(0)


def btn_it1_handler(pin):
    time.sleep(0.05)
    if pin.value() == 0:
        check_gate_logic("IT-0001")

def btn_it2_handler(pin):
    time.sleep(0.05)
    if pin.value() == 0:
        check_gate_logic("IT-0002")

def main():
    global mqtt_client
    connect_wifi()
    broker = cfg.get("MQTT_BROKER")
    mqtt_client = RobustMQTTClient(device_id, broker)
    
    # Subscribe to all status updates
    mqtt_client.subscribe("security/ids/+/status", handle_presence)
    
    if mqtt_client.connect():
        btn_it1.irq(trigger=Pin.IRQ_FALLING, handler=btn_it1_handler)
        btn_it2.irq(trigger=Pin.IRQ_FALLING, handler=btn_it2_handler)
        
        log(device_id, "Ready. Press buttons to simulate gate entry.")
        
        while True:
            mqtt_client.check_msg()
            time.sleep(0.1)

if __name__ == "__main__":
    main()
