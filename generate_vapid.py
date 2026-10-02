import json
import base64
import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

# Generate a new EC key pair (P-256)
private_key = ec.generate_private_key(ec.SECP256R1())

# Get raw bytes
private_numbers = private_key.private_numbers()
private_value = private_numbers.private_value
public_numbers = private_key.public_key().public_numbers()
x = public_numbers.x
y = public_numbers.y

def urlsafe_b64encode_nopad(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=')

priv_bytes = private_value.to_bytes(32, 'big')
pub_bytes = b'\x04' + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')

print("VAPID_PRIVATE_KEY=" + urlsafe_b64encode_nopad(priv_bytes).decode('ascii'))
print("VAPID_PUBLIC_KEY=" + urlsafe_b64encode_nopad(pub_bytes).decode('ascii'))
