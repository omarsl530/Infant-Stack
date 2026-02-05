import network
import time
import ujson
from machine import Pin, Timer
import sys

# Ensure common modules can be found
sys.path.append('/common')

from common.config import cfg
from common.mqtt_client import RobustMQTTClient
from common.security import Security
from common.utils import log

# --- Hardware Setup ---
ALARM_BTN_PIN = 15
STATUS_LED_PIN = 2

alarm_btn = Pin(ALARM_BTN_PIN, Pin.IN, Pin.PULL_UP)
status_led = Pin(STATUS_LED_PIN, Pin.OUT)

# --- State & Data ---
device_id = cfg.get("DEVICE_ID")
if device_id == "UNKNOWN":
    device_id = "IT-0001" # Fallback

secret_key = cfg.get("SECRET_KEY")
security = Security(secret_key)

mqtt_client = None
battery_level = 100
pairing_file = "pairing.json"
mother_id = None

# --- Helpers ---

def load_pairing():
    global mother_id
    try:
        with open(pairing_file, "r") as f:
            data = ujson.load(f)
            mother_id = data.get("mother_id")
            log(device_id, f"Loaded pairing: Mother ID = {mother_id}")
    except:
        log(device_id, "No pairing found.")

def save_pairing(new_mother_id):
    global mother_id
    mother_id = new_mother_id
    with open(pairing_file, "w") as f:
        ujson.dump({"mother_id": mother_id}, f)
    log(device_id, f"Saved pairing: Mother ID = {mother_id}")

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

def make_presence_msg(msg_type="presence"):
    msg = {
        "type": msg_type,
        "device": "IT",
        "id": device_id,
        "battery": battery_level,
        "mother_id": mother_id
    }
    # Sign the message
    return security.sign_message(msg)

def btn_handler(pin):
    # Dedounce simplistic
    time.sleep(0.05)
    if pin.value() == 0:
        log(device_id, "ALARM BUTTON PRESSED!", "ALERT")
        send_alarm()

def send_alarm():
    topic = "security/alerts/" + device_id
    msg = make_presence_msg("alarm")
    msg["alert_code"] = "MANUAL_PANIC"
    mqtt_client.publish(topic, msg)
    # Also publish to gate command or general alert
    mqtt_client.publish("security/alerts/global", msg)
    
    # Blink LED
    for _ in range(5):
        status_led.value(1)
        time.sleep(0.1)
        status_led.value(0)
        time.sleep(0.1)

def pairing_cb(topic, msg):
    try:
        data = ujson.loads(msg)
        if security.verify_signature(data):
            if data.get("type") == "pair_request" and "mother_id" in data:
                # Accept pairing
                new_mom = data["mother_id"]
                log(device_id, f"Received valid pairing request from {new_mom}")
                save_pairing(new_mom)
                # Ack
                ack_topic = f"security/pairing/{new_mom}"
                ack_msg = {
                    "type": "pair_ack",
                    "infant_id": device_id,
                    "mother_id": new_mom
                }
                mqtt_client.publish(ack_topic, security.sign_message(ack_msg))
        else:
            log(device_id, "Received invalid signature on pairing topic", "WARN")
    except Exception as e:
        log(device_id, f"Error processing pairing msg: {e}", "ERROR")

# --- Main Loop ---

def main():
    global mqtt_client, battery_level
    
    connect_wifi()
    
    broker = cfg.get("MQTT_BROKER")
    mqtt_client = RobustMQTTClient(device_id, broker)
    
    # Subscribe to pairing requests tailored to this device
    mqtt_client.subscribe(f"security/pairing/{device_id}", pairing_cb)
    
    if mqtt_client.connect():
        load_pairing()
        
        # Setup Interrupt
        alarm_btn.irq(trigger=Pin.IRQ_FALLING, handler=btn_handler)
        
        last_publish = 0
        publish_interval = cfg.get("PUBLISH_INTERVAL")
        
        while True:
            mqtt_client.check_msg()
            
            now = time.time()
            if now - last_publish >= publish_interval:
                # Periodic Presence
                topic = f"security/ids/{device_id}/status"
                msg = make_presence_msg()
                mqtt_client.publish(topic, msg)
                
                # Check messages again
                mqtt_client.check_msg()
                
                # Drain battery
                battery_level = max(0, battery_level - 1)
                log(device_id, f"Published presence. Batt: {battery_level}%")
                
                last_publish = now
            
            time.sleep(0.1)

if __name__ == "__main__":
    main()
