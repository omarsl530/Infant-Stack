import uhashlib
import ubinascii
import time

class Security:
    def __init__(self, secret_key):
        self.secret_key = secret_key

    def sign_message(self, message_dict):
        """
        Adds a timestamp and signature to the message dictionary.
        Modifies the dictionary in-place.
        """
        # Add timestamp if not present
        if "ts" not in message_dict:
            message_dict["ts"] = int(time.time())
        
        # Create signature
        # Format: key=value|key=value... sorted by key, excluding 'sig'
        payload = self._create_payload_string(message_dict)
        signature = self._hmac_sha256(self.secret_key, payload)
        message_dict["sig"] = signature
        return message_dict

    def verify_signature(self, message_dict):
        """
        Verifies the signature in the message dictionary.
        """
        if "sig" not in message_dict:
            return False
            
        received_sig = message_dict["sig"]
        timestamp = message_dict.get("ts", 0)
        
        # Check timestamp freshness (e.g., within 120 seconds)
        if abs(time.time() - timestamp) > 120:
             # In simulation, time might be tricky, but we'll enforce a window
             # print("Security: Timestamp expired")
             pass # Warn but maybe proceed if strictness allows? Prompts says: "invalid signature or stale timestamp leads to message rejection"
             # Strict check:
             return False

        payload = self._create_payload_string(message_dict)
        calculated_sig = self._hmac_sha256(self.secret_key, payload)
        
        return received_sig == calculated_sig

    def _create_payload_string(self, message_dict):
        """
        Canonicalizes message for signing.
        """
        keys = sorted(message_dict.keys())
        parts = []
        for k in keys:
            if k == "sig":
                continue
            parts.append(f"{k}={message_dict[k]}")
        return "|".join(parts)

    def _hmac_sha256(self, key, msg):
        """
        Simple HMAC-SHA256 implementation using uhashlib.sha256
        """
        # Standard HMAC implementation
        block_size = 64
        if len(key) > block_size:
            key = uhashlib.sha256(key).digest()
        if len(key) < block_size:
            key = key + b'\x00' * (block_size - len(key))

        o_key_pad = bytes(x ^ 0x5c for x in key)
        i_key_pad = bytes(x ^ 0x36 for x in key)

        inner = uhashlib.sha256(i_key_pad + msg.encode()).digest()
        outer = uhashlib.sha256(o_key_pad + inner).digest()
        
        return ubinascii.hexlify(outer).decode()

