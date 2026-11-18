"""The public key that signs releases. A downloaded update is installed only when its
update.json carries a valid Ed25519 signature from the matching secret key. The secret key
lives in the release workflow's secrets and is never in this repository.
"""
PUBLIC_KEY = "f56938c87ab4e3e7c37d27a5f1b7fed2b947050fd12c9e7bb7f8e037c9c8ad6d"
