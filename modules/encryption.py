# carelog/modules/encryption.py

from cryptography.fernet import Fernet

def write_key():
    """Generates a key and saves it into a file."""
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)

def load_key():
    """Loads the key from the current directory."""
    return open("secret.key", "rb").read()

# Generate a key if one doesn't exist
try:
    key = load_key()
except FileNotFoundError:
    write_key()
    key = load_key()

encryptor = Fernet(key)

if __name__ == '__main__':
    print("Encryption key has been generated and saved as 'secret.key'.")