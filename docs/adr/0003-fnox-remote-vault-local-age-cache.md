# fnox secrets: remote vault is the source, local age file is the cache

Secrets resolve from a remote vault (1Password, AWS Secrets Manager, Bitwarden and others) through `fnox get`, with `fnox.toml` committed holding references only. A local age-encrypted file caches the values. Storage strategy stays the user's choice in `fnox.toml`, so one fetch function covers every mode.

Rejected as the recommended default: age-encrypted secrets committed to git. Multi-recipient age needs teammate public keys collected upfront and re-encryption on every join. Departures force rotating every real secret, because git history keeps the old ciphertext forever. A remote vault gives team sharing, MFA and instant revocation without that ceremony.

The cache replaced the macOS-keychain backend: no ACL prompts, encrypted at rest, portable.
