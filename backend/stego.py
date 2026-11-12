from io import BytesIO
from PIL import Image
import struct

MAGIC=b"STEGDATA1"

def embed_bytes(image_bytes,payload):
    try: image=Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as e: raise ValueError("Cover image could not be opened.") from e
    packed=MAGIC+struct.pack(">I",len(payload))+payload
    bits=len(packed)*8; capacity=image.width*image.height*3
    if bits>capacity: raise ValueError(f"Cover image too small: needs {bits} bits; capacity is {capacity} bits.")
    vals=[c for px in image.getdata() for c in px]; idx=0
    for byte in packed:
        for shift in range(7,-1,-1):
            vals[idx]=(vals[idx]&254)|((byte>>shift)&1); idx+=1
    image.putdata([tuple(vals[i:i+3]) for i in range(0,len(vals),3)])
    out=BytesIO(); image.save(out,format="PNG"); return out.getvalue()

def extract_bytes(image_bytes):
    try: image=Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as e: raise ValueError("Retrieved image could not be opened.") from e
    pixels=image.load()
    bits=(channel&1 for y in range(image.height) for x in range(image.width) for channel in pixels[x,y])
    def read(count):
        out=bytearray()
        for _ in range(count):
            v=0
            for _ in range(8):
                try: bit=next(bits)
                except StopIteration as e: raise ValueError("Hidden data is incomplete.") from e
                v=(v<<1)|bit
            out.append(v)
        return bytes(out)
    prefix=read(len(MAGIC)+4)
    if not prefix.startswith(MAGIC): raise ValueError("Image does not contain this application's hidden data.")
    n=struct.unpack(">I",prefix[len(MAGIC):])[0]
    if n<=0 or (len(MAGIC)+4+n)*8>image.width*image.height*3: raise ValueError("Hidden data length is invalid.")
    return read(n)
