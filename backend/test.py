import random
from sqids import Sqids


def get_sqids(salt_string: str) -> Sqids:
    # 1. Base 62 alphabet
    alphabet = list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    # 2. Seed Python's random generator with your secret salt
    rng = random.Random(salt_string)
    rng.shuffle(alphabet)

    # 3. Convert back to a string
    shuffled_alphabet = "".join(alphabet)

    # 4. Initialize Sqids with your scrambled alphabet and a 7-character minimum length
    return Sqids(alphabet=shuffled_alphabet, min_length=7)


# --- Initialize with your secret salt ---
secret_salt = "AJAYNARAYANAN"
sqids = get_sqids(secret_salt)

# --- Example Usage ---
counter = 1000001
uid = sqids.encode([counter])
print(uid)
counts = sqids.decode("Aer232d")

print(counts[0])
