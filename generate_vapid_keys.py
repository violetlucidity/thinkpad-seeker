# generate_vapid_keys.py
# Run this script ONCE to create VAPID keys for Web Push authentication.
# Output will be printed to the console. Paste the values into config.yaml
# under the 'vapid' key (or config.json if using JSON config).
# Do NOT commit config.yaml after adding the private key — it contains a secret.

from py_vapid import Vapid   # py_vapid ships with pywebpush

vapid = Vapid()              # create a new VAPID instance
vapid.generate_keys()        # generate a fresh EC key pair

print("Add these values to config.yaml under the 'vapid' key:\n")
# Serialize keys as hex strings — the format expected by pywebpush
print(f"  public_key:  {vapid.public_key.serialize().hex()}")
print(f"  private_key: {vapid.private_key.serialize().hex()}")
