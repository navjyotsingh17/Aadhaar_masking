from Crypto.Cipher import AES
import base64
import hashlib

def pad(text):
    return text + (16 - len(text) % 16) * chr(16 - len(text) % 16)

def unpad(text):
    return text[:-ord(text[-1])]

def get_key(key_str):
    return hashlib.sha256(key_str.encode()).digest()

def encrypt(message, key_str):
    key = get_key(key_str)
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(message).encode())
    return base64.b64encode(encrypted).decode()

def decrypt(encrypted_message, key_str):
    try:
        key = get_key(key_str)
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted = unpad(cipher.decrypt(base64.b64decode(encrypted_message)).decode())
        return decrypted
    except:
        return 'Error while decrypting'

# Example
secret_key = "Navjyot!"
password = "Masking@101"
encrypted = encrypt(password, secret_key)
decrypted = decrypt(encrypted, secret_key)

full_text = '3700 8734 9014'
clean_text = full_text.replace(" ","")
# print(clean_text)
# print(len(clean_text))

# print("Encrypted:", encrypted)
# print("Decrypted:", decrypted)
