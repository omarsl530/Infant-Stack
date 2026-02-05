import network
import socket
import time
import ujson
import sys
import uselect

sys.path.append('/common')
from common.config import cfg
from common.mqtt_client import RobustMQTTClient
from common.security import Security
from common.utils import log

# --- State ---
device_id = cfg.get("DEVICE_ID")
if device_id == "UNKNOWN":
    device_id = "GT-0001"

mqtt_client = None
events_log = []
alerts_log = []

# --- Web Server Helpers ---
def start_web_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(5)
    s.setblocking(False)
    log(device_id, "Web server started on port 80")
    return s

def handle_web_request(conn):
    try:
        request = conn.recv(1024)
        # Parse simple GET
        response = {
            "device": device_id,
            "uptime": time.time(),
            "alerts": alerts_log[-5:], # Last 5
            "events": events_log[-5:]
        }
        json_resp = ujson.dumps(response)
        
        header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"
        conn.send(header.encode() + json_resp.encode())
        conn.close()
    except Exception as e:
        log(device_id, f"Web error: {e}", "ERROR")
        try: conn.close()
        except: pass

# --- MQTT Callbacks ---

def gate_event_cb(topic, msg):
    try:
        data = ujson.loads(msg)
        # Verify? GT is the authority, should verify.
        # Currently we just log.
        log(device_id, f"GATE EVENT: {data}", "INFO")
        events_log.append({"ts": time.time(), "data": data})
        
        if not data.get("authorized", False):
            # Log Unauthorized attempt
            log(device_id, "UNAUTHORIZED ACCESS ATTEMPT!", "ALERT")
            # Logic to trigger physical alarm could go here (e.g. siren topic)
            
    except Exception as e:
        log(device_id, f"Error processing gate event: {e}", "ERROR")

def alert_cb(topic, msg):
    try:
        data = ujson.loads(msg)
        log(device_id, f"ALARM RECEIVED: {data}", "ALERT")
        alerts_log.append({"ts": time.time(), "data": data})
    except Exception as e:
        log(device_id, f"Error processing alert: {e}", "ERROR")

def command_cb(topic, msg):
    # Log commands for audit
    log(device_id, f"Command Audit: {msg}", "INFO")

# --- Main ---

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

def main():
    global mqtt_client
    connect_wifi()
    
    broker = cfg.get("MQTT_BROKER")
    mqtt_client = RobustMQTTClient(device_id, broker)
    
    mqtt_client.subscribe("security/gate/+/events", gate_event_cb)
    mqtt_client.subscribe("security/alerts/#", alert_cb)
    mqtt_client.subscribe("security/commands/#", command_cb)
    
    server_socket = start_web_server()
    poller = uselect.poll()
    poller.register(server_socket, uselect.POLLIN)
    
    if mqtt_client.connect():
        log(device_id, "System Ready. Monitoring...")
        
        while True:
            mqtt_client.check_msg()
            
            # Check web server
            res = poller.poll(0)
            if res:
                conn, addr = server_socket.accept()
                handle_web_request(conn)
            
            time.sleep(0.1)

if __name__ == "__main__":
    main()
