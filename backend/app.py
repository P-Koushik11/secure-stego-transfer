import os,json,secrets,string,time,base64
from pathlib import Path
from io import BytesIO
from flask import Flask,request,jsonify,send_file
from flask_cors import CORS
from dotenv import load_dotenv
import qrcode
from PIL import Image, UnidentifiedImageError
from crypto_utils import encrypt_file,decrypt_file
from stego import embed_bytes,extract_bytes

load_dotenv()
BASE=Path(__file__).resolve().parent
STORE=Path(os.getenv("STORAGE_DIR","storage"))
if not STORE.is_absolute(): STORE=BASE/STORE
STORE.mkdir(parents=True,exist_ok=True)
TTL=max(1,int(os.getenv("TRANSFER_TTL_HOURS","24")))
MAX_MB=max(1,int(os.getenv("MAX_FILE_MB","10")))
MAX_STEGO_IMAGE_MB=25
MAX_STEGO_PIXELS=25_000_000
FRONTEND=os.getenv("FRONTEND_BASE_URL","https://securestegotransfer.vercel.app").rstrip("/")
FRONTEND_ORIGIN="https://securestegotransfer.vercel.app"
CORS_METHODS=["GET","POST","OPTIONS"]
CORS_HEADERS=["Content-Type","Authorization"]
DEFAULT_CORS_ORIGINS=[FRONTEND_ORIGIN,"http://securestegotransfer.vercel.app"]
CONFIGURED_CORS_ORIGINS=[x.strip().rstrip("/") for x in os.getenv("CORS_ORIGINS","").split(",") if x.strip()]
ORIGINS=list(dict.fromkeys(DEFAULT_CORS_ORIGINS+CONFIGURED_CORS_ORIGINS))
app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=MAX_MB*1024*1024+30*1024*1024

@app.after_request
def add_cors_headers(response):
    if request.path.startswith("/api/") and request.headers.get("Origin")==FRONTEND_ORIGIN:
        response.headers["Access-Control-Allow-Origin"]=FRONTEND_ORIGIN
        response.headers["Access-Control-Allow-Methods"]=", ".join(CORS_METHODS)
        response.headers["Access-Control-Allow-Headers"]=", ".join(CORS_HEADERS)
        response.vary.add("Origin")
    return response

CORS(app,resources={r"^/api/.*$":{
    "origins":ORIGINS,
    "methods":CORS_METHODS,
    "allow_headers":CORS_HEADERS,
    "max_age":600,
}})

def cleanup():
    now=time.time()
    for p in STORE.glob("*.json"):
        try:
            d=json.loads(p.read_text()); img=STORE/d["image_file"]
            if d["expires_at"]<=now:
                if img.parent==STORE: img.unlink(missing_ok=True)
                p.unlink(missing_ok=True)
        except Exception: continue

def make_code():
    alphabet=string.ascii_uppercase+string.digits
    for _ in range(20):
        code="".join(secrets.choice(alphabet) for _ in range(8))
        if not (STORE/f"{code}.json").exists(): return code
    raise RuntimeError("Unable to create unique transfer code.")

@app.get("/api/health")
def health(): return jsonify(status="ok")

@app.post("/api/send")
def send():
    cleanup()
    secret=request.files.get("secret_file"); cover=request.files.get("cover_image"); password=request.form.get("password","")
    if not secret or not cover: return jsonify(error="Choose both a secret file and a cover image."),400
    raw=secret.read(MAX_MB*1024*1024+1)
    if not raw: return jsonify(error="Secret file is empty."),400
    if len(raw)>MAX_MB*1024*1024: return jsonify(error=f"Secret file exceeds {MAX_MB} MB."),413
    cover_bytes=cover.read(25*1024*1024+1)
    if len(cover_bytes)>25*1024*1024: return jsonify(error="Cover image exceeds 25 MB."),413
    try:
        encrypted=encrypt_file(raw,os.path.basename(secret.filename or "download.bin"),secret.mimetype,password)
        png=embed_bytes(cover_bytes,encrypted)
    except ValueError as e: return jsonify(error=str(e)),400
    except Exception:
        app.logger.exception("Create transfer failed")
        return jsonify(error="Unable to create transfer. Check the selected files."),500
    code=make_code(); image_name=f"{code}.png"; expiry=time.time()+TTL*3600
    try:
        (STORE/image_name).write_bytes(png)
        (STORE/f"{code}.json").write_text(json.dumps({"image_file":image_name,"expires_at":expiry}),encoding="utf-8")
    except OSError:
        (STORE/image_name).unlink(missing_ok=True)
        return jsonify(error="Could not temporarily store transfer."),500
    url=f"{FRONTEND}/receive?code={code}"
    qr=qrcode.make(url); buf=BytesIO(); qr.save(buf,format="PNG")
    return jsonify(transfer_code=code,receiver_url=url,qr_code_data_url="data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode(),expires_in_hours=TTL),201

@app.get("/api/transfer-image/<code>")
def transfer_image(code):
    cleanup()
    code=code.strip().upper()
    if len(code)!=8 or not code.isalnum(): return jsonify(error="Transfer image is unavailable."),404
    meta_path=STORE/f"{code}.json"
    if not meta_path.is_file(): return jsonify(error="Transfer image is unavailable."),404
    try: metadata=json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError,ValueError): return jsonify(error="Transfer image is unavailable."),404
    image=STORE/metadata.get("image_file","")
    if image.parent!=STORE or not image.is_file(): return jsonify(error="Transfer image is unavailable."),404
    return send_file(image,mimetype="image/png",download_name=f"{code}.png")

@app.post("/api/receive")
def receive():
    cleanup(); body=request.get_json(silent=True) or {}
    code=str(body.get("transfer_code","")).strip().upper(); password=str(body.get("password",""))
    if len(code)!=8 or not code.isalnum(): return jsonify(error="Transfer code is invalid or expired."),404
    meta_path=STORE/f"{code}.json"
    if not meta_path.exists(): return jsonify(error="Transfer code is invalid or expired."),404
    try: d=json.loads(meta_path.read_text())
    except Exception: return jsonify(error="Transfer metadata is invalid."),404
    image=STORE/d.get("image_file","")
    if image.parent!=STORE or not image.is_file(): return jsonify(error="Transfer image is unavailable."),404
    try: original,info=decrypt_file(extract_bytes(image.read_bytes()),password)
    except ValueError as e: return jsonify(error=str(e)),400
    filename=os.path.basename(str(info.get("filename","download.bin"))) or "download.bin"
    content_type=str(info.get("content_type","application/octet-stream"))
    image.unlink(missing_ok=True); meta_path.unlink(missing_ok=True)
    return send_file(BytesIO(original),mimetype=content_type,as_attachment=True,download_name=filename)

@app.post("/api/receive-image")
def receive_image():
    uploaded=request.files.get("stego_image")
    password=request.form.get("password","")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Choose a stego PNG image to recover the file."),400
    if not password:
        return jsonify(error="Enter the decryption password."),400

    image_bytes=uploaded.read(MAX_STEGO_IMAGE_MB*1024*1024+1)
    if len(image_bytes)>MAX_STEGO_IMAGE_MB*1024*1024:
        return jsonify(error=f"Stego image exceeds {MAX_STEGO_IMAGE_MB} MB."),413
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.format!="PNG":
                return jsonify(error="Unsupported image format. Upload the original stego PNG."),400
            if image.width*image.height>MAX_STEGO_PIXELS:
                return jsonify(error="Stego image dimensions are too large to process."),413
            image.verify()
        encrypted=extract_bytes(image_bytes)
        original,info=decrypt_file(encrypted,password)
    except ValueError:
        return jsonify(error="Could not recover the file. Check the password and use an unmodified stego image."),400
    except (UnidentifiedImageError,OSError,SyntaxError,Image.DecompressionBombError):
        return jsonify(error="The uploaded file is not a valid, supported stego PNG image."),400

    filename=os.path.basename(str(info.get("filename","download.bin")).replace("\\","/")) or "download.bin"
    content_type=str(info.get("content_type","application/octet-stream"))
    return send_file(BytesIO(original),mimetype=content_type,as_attachment=True,download_name=filename)

@app.errorhandler(413)
def too_large(_): return jsonify(error="Request too large. Try smaller files."),413

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
