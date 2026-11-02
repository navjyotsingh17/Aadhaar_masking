from cryptography.fernet import Fernet
import base64

def encrypt(message):
    key = Fernet.generate_key()
    print("Generated Key:", key.decode())
    f = Fernet(key)
    encrypted = f.encrypt(message.encode())
    return base64.b64encode(encrypted).decode(), key

def decrypt(encrypted_message, key):
    try:
        f = Fernet(key)
        decrypted = f.decrypt(base64.b64decode(encrypted_message)).decode()
        return decrypted
    except:
        return 'Error while decrypting'

# Example
secret_key = "Navjyot!"
password = "Masking@101"
# encrypted, key = encrypt(password)
decrypted = decrypt("Z0FBQUFBQnE2RnhvMzdaWGFEOGhlTlFCQU9PZkJ4eHgxcDJRLTZxSnFJc3RteXJjRnBZaUpkOEQ2eXBvdHpiYk53ZGZkNFVhOWZGSGxYNlpzS1NoLWxrRGZPS0IyTEZ1LXc9PQ==", "zOiNs7fH0gfRVmOEo_paJ53HD7nGfIeJxRrQwg0przA=")

# print("Encrypted:", encrypted)
# print("Decrypted:", decrypted)
