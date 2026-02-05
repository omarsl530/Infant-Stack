import time

def log(device_name, message, level="INFO"):
    """
    Simple logging function with timestamp.
    """
    timestamp = time.localtime()
    time_str = "{:02d}:{:02d}:{:02d}".format(timestamp[3], timestamp[4], timestamp[5])
    print(f"[{time_str}] [{device_name}] [{level}] {message}")

def get_timestamp():
    """
    Returns current timestamp. In simulation, this matches the Wokwi simulated time.
    """
    return time.time()
