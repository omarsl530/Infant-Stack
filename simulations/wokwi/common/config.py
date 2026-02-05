import ujson
import os

# Default Configuration
DEFAULTS = {
    "WIFI_SSID": "WOKWI-GUEST",
    "WIFI_PASS": "",
    "MQTT_BROKER": "test.mosquitto.org",
    "MQTT_PORT": 1883,
    "MQTT_USER": "",
    "MQTT_PASS": "",
    "SECRET_KEY": "CHANGE_ME_SECRET",
    "DEVICE_ID": "UNKNOWN",
    "GATE_ID": "GATE-1",
    "PUBLISH_INTERVAL": 10,
    "PRESENCE_EXPIRY": 30,
    "LOW_BATTERY_THRESHOLD": 20
}

class Config:
    def __init__(self):
        self._config = DEFAULTS.copy()
        self.load_specs()

    def load_specs(self):
        """
        Attempts to load simulation_specs.json from the filesystem.
        """
        try:
            with open("simulation_specs.json", "r") as f:
                specs = ujson.load(f)
                # Update config with specs if keys match or mapping is needed
                # Expecting direct key mapping for simplicity or simple transformation
                if "wifi_ssid" in specs: self._config["WIFI_SSID"] = specs["wifi_ssid"]
                if "wifi_pass" in specs: self._config["WIFI_PASS"] = specs["wifi_pass"]
                if "mqtt_broker" in specs: self._config["MQTT_BROKER"] = specs["mqtt_broker"]
                if "secret_key" in specs: self._config["SECRET_KEY"] = specs["secret_key"]
                if "device_id" in specs: self._config["DEVICE_ID"] = specs["device_id"]
                if "gate_id" in specs: self._config["GATE_ID"] = specs["gate_id"]
                
                # Check for deeper keys if structure differs
                # (Simple linear structure assumed based on prompt)
                
        except OSError:
            print("Config: simulation_specs.json not found, using defaults.")
        except Exception as e:
            print(f"Config: Error loading specs: {e}")

    def get(self, key):
        return self._config.get(key, DEFAULTS.get(key))

# Global instance
cfg = Config()
