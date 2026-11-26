# make-licence (for Ernest only)

Makes and checks NSKO QUANT licence keys and signs strategy packs. Works offline.

```
pip install cryptography
python3 tools/make-licence/make_licence.py keygen            # once: makes the signing keypair
python3 tools/make-licence/make_licence.py sign --name "Jane Doe" --email jane@example.com --expiry 2027-12-31 --tier Pro
python3 tools/make-licence/make_licence.py verify NSQ1.xxxx.yyyy
python3 tools/make-licence/make_licence.py sign-pack pack.json > gold.nsqpack
```

- The **private key** is `tools/keys/licence_private.pem`. It is git-ignored. Never commit it, never email it.
  Back it up offline (a USB stick in a drawer). Anyone with it can make licences.
- The **public key** is written into `engine/nsq/licence_key.py`; that one is safe to ship.
- Running `keygen --force` makes a new keypair: every licence signed with the old key stops working.
- Tiers: `Standard` or `Pro`. Expiry is a date (`YYYY-MM-DD`); the licence is valid up to and including that day.
