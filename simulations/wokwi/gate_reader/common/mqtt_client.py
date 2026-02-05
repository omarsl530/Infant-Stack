from umqtt.simple import MQTTClient
import time
import ujson
from common.utils import log

class RobustMQTTClient:
    def __init__(self, client_id, broker, user=None, password=None, port=1883):
        self.client_id = client_id
        self.broker = broker
        self.client = MQTTClient(client_id, broker, user=user, password=password, port=port)
        self.client.set_callback(self.sub_cb)
        self.callbacks = {}

    def sub_cb(self, topic, msg):
        topic_str = topic.decode()
        if topic_str in self.callbacks:
            self.callbacks[topic_str](topic, msg)
        else:
            # Handle wildcard subscriptions if necessary, or default logging
            log(self.client_id, f"Received message on {topic_str}: {msg}")
            
            # Simple exact match fallback didn't work, try iterating patterns if needed
            # For now, simplistic exact match
            for t, cb in self.callbacks.items():
                if t.endswith("#") and topic_str.startswith(t[:-1]):
                    cb(topic, msg) 
                    return
                if "+" in t:
                    # simplistic wildcard support for single level would go here
                    pass

    def connect(self):
        try:
            self.client.connect()
            log(self.client_id, "Connected to MQTT Broker")
            return True
        except Exception as e:
            log(self.client_id, f"Failed to connect to MQTT Broker: {e}", "ERROR")
            return False

    def subscribe(self, topic, callback):
        self.callbacks[topic] = callback
        self.client.subscribe(topic)
        log(self.client_id, f"Subscribed to {topic}")

    def publish(self, topic, message_dict):
        try:
            payload = ujson.dumps(message_dict)
            self.client.publish(topic, payload)
            # log(self.client_id, f"Published to {topic}") # Verbose
        except Exception as e:
            log(self.client_id, f"Failed to publish: {e}", "ERROR")

    def check_msg(self):
        try:
            self.client.check_msg()
        except Exception as e:
            log(self.client_id, f"Error checking messages: {e}", "ERROR")
            # Reconnect logic could go here
            self.reconnect()

    def reconnect(self):
        log(self.client_id, "Attempting reconnect...", "WARN")
        time.sleep(2)
        try:
            self.client.connect()
            # Resubscribe
            for topic in self.callbacks.keys():
                self.client.subscribe(topic)
            log(self.client_id, "Reconnected!")
        except Exception as e:
            log(self.client_id, f"Reconnect failed: {e}", "ERROR")
