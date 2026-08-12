# Demo keys — no trust, on purpose

The RSA keypair in this directory — **including the private key** — is
intentionally committed to this public repository. It exists solely so the
examples, tests, and demo scripts can produce and verify signed license
documents without any private infrastructure.

Because the private key is public:

- A license signed with it proves nothing. Anyone can mint one.
- Never ship `public_key.pem` as the trust root of a real product.
- Never accept licenses signed by `private_key.pem` in production.
- Never reuse this keypair anywhere outside this repository's demos.

A real deployment generates its own keypair inside a private signing
authority, keeps the private key there, and embeds only its *own* public key
in the shipped application. That production authority is a separate, private
project and is deliberately not part of this repository.

To regenerate the demo keypair (and then re-sign the example license):

```bash
python demo_keys/generate_demo_keys.py
python scripts/build_demo_license.py
```
