import network
import time
import ujson
from machine import Pin
import sys
import os

# Ensure common modules can be found
sys.path.append('/common')

from common.config import cfg
from common.mqtt_client import RobustMQTTClient
from common.security import Security
from common.utils import log

# --- Hardware Setup ---
PAIR_BTN_PIN = 14
CANCEL_BTN_PIN = 12
STATUS_LED_PIN = 2

pair_btn = Pin(PAIR_BTN_PIN, Pin.IN, Pin.PULL_UP)
cancel_btn = Pin(CANCEL_BTN_PIN, Pin.IN, Pin.PULL_UP)
status_led = Pin(STATUS_LED_PIN, Pin.OUT)

# --- State & Data ---
device_id = cfg.get("DEVICE_ID")
if device_id == "UNKNOWN":
    device_id = "MT-0001"

target_infant_id = "IT-0001" # Default target for simulation
# In a real scenario, this might be discovered via BLE scan or user input.
# For simulation, we assume we want to pair with IT-0001.

secret_key = cfg.get("SECRET_KEY")
security = Security(secret_key)
mqtt_client = None

pairing_file = "pairing.json"
paired_infant_id = None

# --- Helpers ---

def load_pairing():
    global paired_infant_id
    try:
        with open(pairing_file, "r") as f:
            data = ujson.load(f)
            paired_infant_id = data.get("infant_id")
            log(device_id, f"Loaded pairing: Infant ID = {paired_infant_id}")
    except:
        log(device_id, "No pairing found.")

def save_pairing(infant_id):
    global paired_infant_id
    paired_infant_id = infant_id
    with open(pairing_file, "w") as f:
        ujson.dump({"infant_id": paired_infant_id}, f)
    log(device_id, f"Saved pairing: Infant ID = {paired_infant_id}")

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

def make_msg(msg_type, extra_fields=None):
    msg = {
        "type": msg_type,
        "device": "MT",
        "id": device_id
    }
    if extra_fields:
        msg.update(extra_fields)
    return security.sign_message(msg)

def btn_pair_handler(pin):
    time.sleep(0.05)
    if pin.value() == 0:
        log(device_id, "PAIR BUTTON PRESSED")
        # Initiate pairing with target
        topic = f"security/pairing/{target_infant_id}"
        msg = make_msg("pair_request", {"mother_id": device_id})
        mqtt_client.publish(topic, msg)
        blink(2)

def btn_cancel_handler(pin):
    time.sleep(0.05)
    if pin.value() == 0:
        log(device_id, "CANCEL BUTTON PRESSED")
        if paired_infant_id:
            # Send cancel command to GT
            topic = "security/commands/cancel"
            msg = make_msg("cancel_alarm", {
                "mother_id": device_id,
                "infant_id": paired_infant_id
            })
            mqtt_client.publish(topic, msg)
            blink(3)
        else:
            log(device_id, "Ignored Cancel: Not paired", "WARN")

def blink(limit):
    for _ in range(limit):
        status_led.value(1)
        time.sleep(0.2)
        status_led.value(0)
        time.sleep(0.2)

def pairing_ack_cb(topic, msg):
    try:
        data = ujson.loads(msg)
        if security.verify_signature(data):
            if data.get("type") == "pair_ack" and data.get("mother_id") == device_id:
                new_infant = data.get("infant_id")
                log(device_id, f"Pairing SUCCESS with {new_infant}!", "SUCCESS")
                save_pairing(new_infant)
                blink(5)
    except Exception as e:
        log(device_id, f"Error processing ack: {e}", "ERROR")

# --- Main Loop ---

def main():
    global mqtt_client
    
    connect_wifi()
    
    broker = cfg.get("MQTT_BROKER")
    mqtt_client = RobustMQTTClient(device_id, broker)
    
    # Subscribe to own pairing channel for ACKs
    mqtt_client.subscribe(f"security/pairing/{device_id}", pairing_ack_cb)
    
    if mqtt_client.connect():
        load_pairing()
        
        pair_btn.irq(trigger=Pin.IRQ_FALLING, handler=btn_pair_handler)
        cancel_btn.irq(trigger=Pin.IRQ_FALLING, handler=btn_cancel_handler)
        
        last_publish = 0
        publish_interval = cfg.get("PUBLISH_INTERVAL")
        
        while True:
            mqtt_client.check_msg()
            
            now = time.time()
            if now - last_publish >= publish_interval:
                # Presence
                topic = f"security/ids/{device_id}/status"
                msg = make_msg("presence")
                mqtt_client.publish(topic, msg)
                last_publish = now
                log(device_id, "Published presence")
            
            time.sleep(0.1)

if __name__ == "__main__":
    main()
