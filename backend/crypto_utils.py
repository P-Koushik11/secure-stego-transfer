import json, struct
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
from Crypto.Random import get_random_bytes

MAGIC=b"SDTIS1"; SALT_LEN=16; NONCE_LEN=12; TAG_LEN=16

def encrypt_file(file_bytes, filename, content_type, password):
    if not password or len(password) < 8:
        raise ValueError("Use a password with at least 8 characters.")
    meta=json.dumps({"filename":filename or "download.bin","content_type":content_type or "application/octet-stream"},separators=(",",":")).encode()
    plain=struct.pack(">H",len(meta))+meta+file_bytes
    salt=get_random_bytes(SALT_LEN); nonce=get_random_bytes(NONCE_LEN)
    key=scrypt(password.encode(),salt,32,N=2**14,r=8,p=1)
    cipher=AES.new(key,AES.MODE_GCM,nonce=nonce,mac_len=TAG_LEN)
    ciphertext,tag=cipher.encrypt_and_digest(plain)
    return MAGIC+salt+nonce+ciphertext+tag

def decrypt_file(data,password):
    header=len(MAGIC)+SALT_LEN+NONCE_LEN
    if len(data)<header+TAG_LEN+2 or not data.startswith(MAGIC):
        raise ValueError("No valid encrypted payload was found.")
    i=len(MAGIC); salt=data[i:i+SALT_LEN]; i+=SALT_LEN
    nonce=data[i:i+NONCE_LEN]; i+=NONCE_LEN
    key=scrypt(password.encode(),salt,32,N=2**14,r=8,p=1)
    cipher=AES.new(key,AES.MODE_GCM,nonce=nonce,mac_len=TAG_LEN)
    try: plain=cipher.decrypt_and_verify(data[i:-TAG_LEN],data[-TAG_LEN:])
    except ValueError as e: raise ValueError("Incorrect password or hidden data is corrupted.") from e
    n=struct.unpack(">H",plain[:2])[0]
    try: meta=json.loads(plain[2:2+n].decode())
    except Exception as e: raise ValueError("Decrypted metadata is invalid.") from e
    return plain[2+n:],meta
