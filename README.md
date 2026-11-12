# Secure Data Transfer Over Internet Using Image Steganography

React + Vite frontend, Flask backend, AES-GCM encryption, Scrypt key derivation, Pillow LSB steganography, QR transfer links and temporary storage.

## Run on Windows / VS Code

### Backend terminal
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```
Backend: http://127.0.0.1:5000

### Frontend terminal (second terminal)
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```
Frontend: http://localhost:5173

## Use
Choose a secret file (maximum 10 MB), a sufficiently large cover image, and a password of at least 8 characters. Create transfer, then share the code or QR link and send the password through a separate channel. Receiver enters code and password. On successful decryption, the transfer is deleted. Transfers expire after 24 hours by default.

## Important
- The QR contains only the receiver URL and transfer code, never the password.
- Stego images are written as PNG; don't resize or JPEG-compress them.
- The starter implementation performs decryption on the Flask server. It is an educational MVP, not an audited security product. Use HTTPS, a production WSGI server and strict CORS before any public deployment. Do not expose Flask's debug server to the public Internet.
- The default QR URL works on the same computer only. For cross-device or Internet use, configure `FRONTEND_BASE_URL`, `VITE_API_BASE_URL`, and CORS origins with reachable deployment URLs.

## Deployment configuration

For the deployed frontend at `https://securestegotransfer.vercel.app` and backend at `https://secure-stego-transfer.onrender.com`:

- In Render, set `CORS_ORIGINS` to `https://securestegotransfer.vercel.app` and `FRONTEND_BASE_URL` to that same URL. Set the service root directory to `backend`, install with `pip install -r requirements.txt`, and use `gunicorn app:app` as the start command.
- In Vercel, set `VITE_API_BASE_URL` to `https://secure-stego-transfer.onrender.com/api`, then redeploy so the setting is included in the frontend build. The frontend also defaults to this backend URL for production builds when the variable is omitted.
- Flask-CORS handles API `OPTIONS` preflights and allows `GET`, `POST`, `OPTIONS`, `Content-Type`, and `Authorization`; the current frontend uses `Content-Type` for JSON receive requests and does not send an Authorization header.
- The sender can also preview and download the generated PNG. Receivers may upload that unchanged PNG and password to recover the original file without using a transfer code; uploaded stego images are processed in memory and limited to 25 MB and 25 million pixels. Transfer-code recovery and its expiring temporary storage remain available.
