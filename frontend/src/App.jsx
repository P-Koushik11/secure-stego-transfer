import { useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  CheckCircle2,
  Copy,
  Download,
  FileImage,
  FileUp,
  KeyRound,
  LockKeyhole,
  QrCode,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";

const DEFAULT_API = import.meta.env.PROD
  ? "https://secure-stego-transfer.onrender.com/api"
  : "http://127.0.0.1:5000/api";
const API = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API).replace(
  /\/$/,
  "",
);

const size = (n) =>
  n < 1024
    ? `${n} B`
    : n < 1048576
      ? `${(n / 1024).toFixed(1)} KB`
      : `${(n / 1048576).toFixed(2)} MB`;

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name || "received-file";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function App() {
  const params = new URLSearchParams(location.search);
  const [mode, setMode] = useState(params.has("code") ? "receive" : "send");
  const [secret, setSecret] = useState(null);
  const [cover, setCover] = useState(null);
  const [sendPass, setSendPass] = useState("");
  const [code, setCode] = useState(params.get("code") || "");
  const [receivePass, setReceivePass] = useState("");
  const [receiveMethod, setReceiveMethod] = useState("code");
  const [stegoFile, setStegoFile] = useState(null);
  const [transfer, setTransfer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [downloadingStego, setDownloadingStego] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function send(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setTransfer(null);

    if (!secret || !cover) {
      return setError("Choose both a secret file and a cover image.");
    }
    if (sendPass.length < 8) {
      return setError("Use a password with at least 8 characters.");
    }

    const formData = new FormData();
    formData.append("secret_file", secret);
    formData.append("cover_image", cover);
    formData.append("password", sendPass);
    setBusy(true);

    try {
      const response = await fetch(`${API}/send`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw Error(data.error || "Could not create transfer.");
      }
      setTransfer(data);
      setNotice("Transfer created. Share the password separately.");
      setSendPass("");
    } catch (requestError) {
      setError(requestError.message || "Could not connect to backend.");
    } finally {
      setBusy(false);
    }
  }

  async function receive(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (receiveMethod === "image" && !stegoFile) {
      return setError("Choose the stego PNG image to recover the file.");
    }
    setBusy(true);

    try {
      let response;
      if (receiveMethod === "image") {
        const formData = new FormData();
        formData.append("stego_image", stegoFile);
        formData.append("password", receivePass);
        response = await fetch(`${API}/receive-image`, {
          method: "POST",
          body: formData,
        });
      } else {
        response = await fetch(`${API}/receive`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transfer_code: code.trim(),
            password: receivePass,
          }),
        });
      }
      if (!response.ok) {
        const data = await response.json();
        throw Error(data.error || "Could not retrieve file.");
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get("Content-Disposition") || "";
      const filename = contentDisposition.match(/filename="?([^";]+)"?/i);
      download(blob, filename?.[1] || "received-file");
      setReceivePass("");
      setNotice(
        receiveMethod === "image"
          ? "Stego image authenticated. Your file was recovered and downloaded."
          : "File decrypted and downloaded. The transfer was consumed.",
      );
    } catch (requestError) {
      setError(requestError.message || "Could not connect to backend.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadStegoImage() {
    if (!transfer) return;
    setError("");
    setDownloadingStego(true);
    try {
      const response = await fetch(
        `${API}/transfer-image/${transfer.transfer_code}`,
      );
      if (!response.ok) {
        const data = await response.json();
        throw Error(data.error || "Could not download the stego image.");
      }
      download(await response.blob(), `stegosafe-${transfer.transfer_code}.png`);
    } catch (requestError) {
      setError(requestError.message || "Could not download the stego image.");
    } finally {
      setDownloadingStego(false);
    }
  }

  async function copy(value) {
    try {
      await navigator.clipboard.writeText(value);
      setNotice("Copied to clipboard.");
    } catch {
      setNotice("Copy unavailable; select the text and copy it manually.");
    }
  }

  function selectMode(nextMode) {
    setMode(nextMode);
    setError("");
    setNotice("");
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <a
            className="brand"
            href="/"
            onClick={(event) => {
              event.preventDefault();
              selectMode("send");
            }}
            aria-label="StegoSafe home"
          >
            <span className="brand-mark">
              <ShieldCheck size={21} strokeWidth={2.2} />
            </span>
            <span className="brand-copy">
              <span className="brand-name">
                Stego<span>Safe</span>
              </span>
              <span className="brand-caption">PRIVATE FILE TRANSFER</span>
            </span>
          </a>
          <div className="header-assurance">
            <LockKeyhole size={15} />
            <span>AES-GCM protected</span>
          </div>
        </div>
      </header>

      <main className="page-content">
        <section className="intro" aria-labelledby="page-title">
          <div className="intro-copy">
            <span className="eyebrow">
              <span className="eyebrow-dot" />
              PRIVATE BY DESIGN
            </span>
            <h1 id="page-title">
              Send files quietly.
              <br />
              <span>Keep them protected.</span>
            </h1>
            <p>
              Encrypt a file, conceal it inside an image, and share it with a
              one-time transfer code.
            </p>
          </div>
          <div className="process-note" aria-label="How it works">
            <span className="process-number">01—03</span>
            <span>Encrypt</span>
            <span className="process-separator">/</span>
            <span>Conceal</span>
            <span className="process-separator">/</span>
            <span>Transfer</span>
          </div>
        </section>

        <section className="transfer-panel" aria-label="Secure file transfer">
          <nav className="mode-tabs" aria-label="Transfer mode">
            <button
              className={mode === "send" ? "mode-tab active" : "mode-tab"}
              type="button"
              onClick={() => selectMode("send")}
              aria-current={mode === "send" ? "page" : undefined}
            >
              <FileUp size={17} />
              Send a file
            </button>
            <button
              className={mode === "receive" ? "mode-tab active" : "mode-tab"}
              type="button"
              onClick={() => selectMode("receive")}
              aria-current={mode === "receive" ? "page" : undefined}
            >
              <ArrowDownToLine size={17} />
              Receive a file
            </button>
          </nav>

          {error && (
            <div className="alert error" role="alert">
              <span className="alert-mark">!</span>
              {error}
            </div>
          )}
          {notice && (
            <div className="alert success" role="status">
              <CheckCircle2 size={17} />
              {notice}
            </div>
          )}

          {mode === "send" ? (
            <article className="transfer-card">
              <div className="card-heading">
                <div>
                  <span className="section-kicker">SECURE SENDER</span>
                  <h2>Create a transfer</h2>
                  <p>Your file is encrypted before it is hidden in the image.</p>
                </div>
                <span className="step-count">01 <i>/</i> 02</span>
              </div>

              <form onSubmit={send}>
                <div className="field-group">
                  <label htmlFor="secret-file">
                    <span className="field-number">01</span>
                    Secret file
                    <em>Max 10 MB</em>
                  </label>
                  <label className="file-picker" htmlFor="secret-file">
                    <input
                      id="secret-file"
                      type="file"
                      onChange={(event) =>
                        setSecret(event.target.files?.[0] || null)
                      }
                    />
                    <span className="picker-icon">
                      <UploadCloud size={20} />
                    </span>
                    <span className="picker-copy">
                      <strong>
                        {secret ? secret.name : "Choose a file to protect"}
                      </strong>
                      <small>
                        {secret
                          ? size(secret.size)
                          : "Documents, archives, text files and more"}
                      </small>
                    </span>
                    <span className="picker-action">Browse</span>
                  </label>
                </div>

                <div className="field-group">
                  <label htmlFor="cover-image">
                    <span className="field-number">02</span>
                    Cover image
                    <em>Larger images carry more data</em>
                  </label>
                  <label className="file-picker" htmlFor="cover-image">
                    <input
                      id="cover-image"
                      type="file"
                      accept="image/*"
                      onChange={(event) =>
                        setCover(event.target.files?.[0] || null)
                      }
                    />
                    <span className="picker-icon">
                      <FileImage size={20} />
                    </span>
                    <span className="picker-copy">
                      <strong>
                        {cover
                          ? cover.name
                          : "Choose an ordinary-looking image"}
                      </strong>
                      <small>
                        {cover ? size(cover.size) : "The result is stored as PNG"}
                      </small>
                    </span>
                    <span className="picker-action">Browse</span>
                  </label>
                </div>

                <div className="field-group">
                  <label htmlFor="send-password">
                    <span className="field-number">03</span>
                    Decryption password
                  </label>
                  <div className="text-input">
                    <KeyRound size={17} />
                    <input
                      id="send-password"
                      type="password"
                      minLength="8"
                      autoComplete="new-password"
                      placeholder="At least 8 characters"
                      value={sendPass}
                      onChange={(event) => setSendPass(event.target.value)}
                      required
                    />
                  </div>
                  <p className="field-hint">
                    Share this password separately. It is never included in the
                    QR code.
                  </p>
                </div>

                <button className="primary-button" disabled={busy}>
                  {busy ? (
                    "Encrypting and hiding data…"
                  ) : (
                    <>
                      Create secure transfer <ArrowRight size={17} />
                    </>
                  )}
                </button>
              </form>

              {transfer && (
                <div className="result-panel">
                  <div className="stego-download-card">
                    <img
                      src={`${API}/transfer-image/${transfer.transfer_code}`}
                      alt="Preview of the generated stego image"
                    />
                    <div className="stego-download-copy">
                      <h3>Stego image ready</h3>
                      <p>
                        Keep this original PNG unchanged to recover the file
                        without a transfer code.
                      </p>
                      <button
                        className="primary-button"
                        type="button"
                        onClick={downloadStegoImage}
                        disabled={downloadingStego}
                      >
                        <Download size={16} />
                        {downloadingStego
                          ? "Preparing download…"
                          : "Download Stego Image"}
                      </button>
                    </div>
                  </div>

                  <div className="result-heading">
                    <span className="result-icon">
                      <CheckCircle2 size={18} />
                    </span>
                    <div>
                      <h3>Your transfer is ready</h3>
                      <p>
                        Temporary storage · expires in about{" "}
                        {transfer.expires_in_hours} hours
                      </p>
                    </div>
                  </div>

                  <div className="code-field">
                    <label htmlFor="transfer-code">Transfer code</label>
                    <div className="code-box">
                      <code id="transfer-code">{transfer.transfer_code}</code>
                      <button
                        type="button"
                        onClick={() => copy(transfer.transfer_code)}
                        aria-label="Copy transfer code"
                      >
                        <Copy size={16} />
                        <span>Copy code</span>
                      </button>
                    </div>
                  </div>

                  <div className="qr-card">
                    <img
                      src={transfer.qr_code_data_url}
                      alt="QR code for the receiver page and transfer code"
                    />
                    <div className="qr-copy">
                      <h4>Ready to share</h4>
                      <p>
                        Scan to open the receiver page. The QR code contains
                        the link and transfer code—not the password.
                      </p>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => copy(transfer.receiver_url)}
                      >
                        <Copy size={14} /> Copy receiver link
                      </button>
                    </div>
                  </div>

                  <p className="security-reminder">
                    <LockKeyhole size={15} />
                    Keep the password private and send it through a separate
                    channel.
                  </p>
                </div>
              )}
            </article>
          ) : (
            <article className="transfer-card">
              <div className="card-heading">
                <div>
                  <span className="section-kicker">SECURE RECEIVER</span>
                  <h2>Retrieve your file</h2>
                  <p>Recover with a transfer code or your saved stego image.</p>
                </div>
                <span className="step-count">02 <i>/</i> 02</span>
              </div>

              <form onSubmit={receive}>
                <div
                  className="recovery-methods"
                  role="group"
                  aria-label="Recovery method"
                >
                  <button
                  className={
                    receiveMethod === "code" ? "mode-tab active" : "mode-tab"
                  }
                  type="button"
                  onClick={() => setReceiveMethod("code")}
                  aria-pressed={receiveMethod === "code"}
                  >
                  <QrCode size={16} /> Transfer code
                  </button>
                  <button
                  className={
                    receiveMethod === "image"
                      ? "mode-tab active"
                      : "mode-tab"
                  }
                  type="button"
                  onClick={() => setReceiveMethod("image")}
                  aria-pressed={receiveMethod === "image"}
                  >
                  <FileImage size={16} /> Upload stego image
                  </button>
                </div>

                {receiveMethod === "code" ? (
                  <div className="field-group">
                  <label htmlFor="transfer-code-input">
                    <span className="field-number">01</span>
                    Transfer code
                  </label>
                  <div className="text-input">
                    <QrCode size={17} />
                    <input
                      id="transfer-code-input"
                      maxLength="8"
                      placeholder="e.g. A1B2C3D4"
                      value={code}
                      onChange={(event) =>
                        setCode(event.target.value.toUpperCase())
                      }
                      required
                    />
                  </div>
                  </div>
                ) : (
                  <div className="field-group">
                  <label htmlFor="stego-image-input">
                    <span className="field-number">01</span>
                    Stego PNG image
                  </label>
                  <label className="file-picker" htmlFor="stego-image-input">
                    <input
                      id="stego-image-input"
                      type="file"
                      accept="image/png"
                      onChange={(event) =>
                        setStegoFile(event.target.files?.[0] || null)
                      }
                    />
                    <span className="picker-icon">
                      <FileImage size={20} />
                    </span>
                    <span className="picker-copy">
                      <strong>
                        {stegoFile
                          ? stegoFile.name
                          : "Choose the downloaded stego image"}
                      </strong>
                      <small>
                        {stegoFile
                          ? size(stegoFile.size)
                          : "Use the original PNG without resizing or recompressing"}
                      </small>
                    </span>
                    <span className="picker-action">Browse</span>
                  </label>
                  </div>
                )}

                <div className="field-group">
                  <label htmlFor="receive-password">
                  <span className="field-number">02</span>
                  Decryption password
                  </label>
                  <div className="text-input">
                  <KeyRound size={17} />
                  <input
                    id="receive-password"
                    type="password"
                    autoComplete="current-password"
                    placeholder="Enter the password"
                    value={receivePass}
                    onChange={(event) => setReceivePass(event.target.value)}
                    required
                  />
                  </div>
                </div>

                <div className="privacy-note">
                  <ShieldCheck size={19} />
                  <span>
                    <b>Authenticated decryption</b>
                    <small>
                      If the password is wrong or data was altered,
                      authentication fails and no file is downloaded.
                    </small>
                  </span>
                </div>

                <button className="primary-button" disabled={busy}>
                  {busy ? (
                    "Retrieving and decrypting…"
                  ) : (
                    <>
                      {receiveMethod === "image"
                        ? "Decrypt & Recover File"
                        : "Decrypt and download"}
                      <ArrowDownToLine size={17} />
                    </>
                  )}
                </button>
              </form>
            </article>
          )}
        </section>

        <section className="trust-row" aria-label="Transfer protections">
          <div className="trust-item">
            <span className="trust-icon">
              <LockKeyhole size={18} />
            </span>
            <span>
              <b>AES-GCM encryption</b>
              <small>Confidentiality and integrity</small>
            </span>
          </div>
          <div className="trust-item">
            <span className="trust-icon">
              <FileImage size={18} />
            </span>
            <span>
              <b>LSB steganography</b>
              <small>Hidden in a PNG image</small>
            </span>
          </div>
          <div className="trust-item">
            <span className="trust-icon">
              <CheckCircle2 size={18} />
            </span>
            <span>
              <b>One-time retrieval</b>
              <small>Deleted after success</small>
            </span>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <span>StegoSafe · Academic project prototype</span>
          <span>Never share the password with the transfer code.</span>
        </div>
      </footer>
    </div>
  );
}
