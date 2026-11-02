import { useEffect, useRef, useState } from 'react';
import { validateImage } from './validateImage';

interface PlateBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  confidence: number;
}

interface PlateCorner {
  x: number;
  y: number;
  confidence: number | null;
}

interface PlatePreview {
  image: string;
  text: string;
  aligned: boolean;
  corners: PlateCorner[];
}

function ImageIcon() {
  return (
    <svg width="38" height="38" viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="34" height="34" rx="2" stroke="currentColor" strokeWidth="3" />
      <path d="m8 30 8-9 5 5 5-7 7 11H8Z" fill="currentColor" />
    </svg>
  );
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ text: string; kind: 'status' | 'error' } | null>(null);
  const [dragging, setDragging] = useState(false);
  const [boxes, setBoxes] = useState<PlateBox[]>([]);
  const [plates, setPlates] = useState<PlatePreview[]>([]);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);
  const uploadInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (preview) return () => URL.revokeObjectURL(preview);
  }, [preview]);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!notification) return;
    const timer = window.setTimeout(() => setNotification(null), 6000);
    return () => window.clearTimeout(timer);
  }, [notification]);

  function chooseFile(next: File | undefined) {
    if (!next) return;
    const message = validateImage(next);
    setNotification(message ? { text: message, kind: 'error' } : null);
    if (message) return;
    request.current?.abort();
    setLoading(false);
    setBoxes([]);
    setPlates([]);
    setImageSize(null);
    setFile(next);
    setPreview(URL.createObjectURL(next));
  }

  async function detectPlates() {
    if (!file) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setNotification({ text: 'Đang phát hiện biển số...', kind: 'status' });
    setBoxes([]);
    setPlates([]);
    const body = new FormData();
    body.append('file', file);
    try {
      const response = await fetch('/api/v1/ocr/detect', { method: 'POST', body, signal: controller.signal });
      if (!response.ok) throw new Error('Detection failed');
      const data: unknown = await response.json();
      if (
        !data ||
        typeof data !== 'object' ||
        !('boxes' in data) ||
        !Array.isArray(data.boxes) ||
        !data.boxes.every(
          (box: PlateBox) =>
            box && ['x1', 'y1', 'x2', 'y2', 'confidence'].every((key) => Number.isFinite(box[key as keyof PlateBox])),
        ) ||
        !('plates' in data) ||
        !Array.isArray(data.plates) ||
        data.plates.length !== data.boxes.length ||
        !data.plates.every(
          (plate: PlatePreview) =>
            plate &&
            typeof plate.image === 'string' &&
            typeof plate.text === 'string' &&
            typeof plate.aligned === 'boolean' &&
            Array.isArray(plate.corners) &&
            (plate.corners.length === 0 || plate.corners.length === 4) &&
            plate.corners.every(
              (corner) =>
                corner &&
                Number.isFinite(corner.x) &&
                Number.isFinite(corner.y) &&
                (corner.confidence === null || Number.isFinite(corner.confidence)),
            ),
        )
      ) {
        throw new Error('Invalid detection response');
      }
      if (controller.signal.aborted) return;
      setBoxes(data.boxes);
      setPlates(data.plates);
      setNotification({
        text: data.boxes.length ? `Đã phát hiện ${data.boxes.length} biển số.` : 'Không tìm thấy biển số.',
        kind: 'status',
      });
    } catch {
      if (!controller.signal.aborted) {
        setNotification({ text: 'Không thể phát hiện biển số. Vui lòng thử lại.', kind: 'error' });
      }
    } finally {
      if (request.current === controller) {
        request.current = null;
        setLoading(false);
      }
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">
            <svg viewBox="0 0 36 36" fill="none">
              <path
                d="M4 13V9a5 5 0 0 1 5-5h4M23 4h4a5 5 0 0 1 5 5v4M32 23v4a5 5 0 0 1-5 5h-4M13 32H9a5 5 0 0 1-5-5v-4"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
              />
              <circle cx="18" cy="18" r="8" stroke="currentColor" strokeWidth="3" />
              <circle cx="18" cy="18" r="2" fill="currentColor" />
            </svg>
          </span>
          <strong>License Plate Recognition</strong>
        </div>
        <div className="account">
          <span className="avatar" aria-hidden="true">
            N
          </span>
          <span>Người dùng</span>
        </div>
      </header>

      <main>
        <nav className="breadcrumbs" aria-label="Đường dẫn">
          <span>Sản phẩm</span>
          <span aria-hidden="true">›</span>
          <span>License Plate Recognition</span>
        </nav>
        <div className="workspace">
          <section className="upload-card" aria-labelledby="upload-title">
            <div className="upload-header">
              <h1 id="upload-title">Tải hình ảnh</h1>
              <button type="button" className="upload-button" onClick={() => uploadInput.current?.click()}>
                {file ? 'Chọn ảnh khác' : 'Tải ảnh'}
              </button>
            </div>
            <div className="card-body">
              <label
                className={`dropzone${preview ? ' has-preview' : ''}${dragging ? ' dragging' : ''}`}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={(event) => {
                  event.preventDefault();
                  setDragging(false);
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragging(false);
                  chooseFile(event.dataTransfer.files[0]);
                }}
              >
                <input
                  ref={uploadInput}
                  aria-label="Chọn ảnh"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) => {
                    chooseFile(event.target.files?.[0]);
                    event.target.value = '';
                  }}
                />
                {preview ? (
                  <>
                    <span className="preview-frame">
                      <img
                        src={preview}
                        alt="Ảnh đã chọn"
                        className="preview"
                        onLoad={(event) =>
                          setImageSize({
                            width: event.currentTarget.naturalWidth,
                            height: event.currentTarget.naturalHeight,
                          })
                        }
                      />
                      {imageSize && boxes.length ? (
                        <svg
                          className="plate-boxes"
                          viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
                          preserveAspectRatio="xMidYMid meet"
                          aria-hidden="true"
                        >
                          {plates.map((plate, index) =>
                            plate.aligned && plate.corners.length === 4 ? (
                              <polygon
                                key={index}
                                points={plate.corners.map((corner) => `${corner.x},${corner.y}`).join(' ')}
                              />
                            ) : null,
                          )}
                        </svg>
                      ) : null}
                    </span>
                    <span className="preview-actions">
                      <small>{file?.name}</small>
                    </span>
                  </>
                ) : (
                  <>
                    <ImageIcon />
                    <span className="drop-caption">
                      Kéo ảnh vào đây hoặc <em>chọn tệp</em>
                    </span>
                    <small>JPG, PNG hoặc WEBP · Tối đa 10 MB</small>
                  </>
                )}
              </label>
              {file ? (
                <button type="button" className="detect-button" onClick={detectPlates} disabled={loading}>
                  Phát hiện biển số
                </button>
              ) : null}
            </div>
          </section>
          <aside className="plate-sidebar" aria-labelledby="plates-title">
            <h2 id="plates-title">Ảnh biển số</h2>
            {plates.length ? (
              <ol className="plate-list">
                {plates.map((plate, index) => (
                  <li key={index}>
                    <span>Biển số {index + 1}</span>
                    <div className="plate-result">
                      <div className="plate-image">
                        <img
                          src={`data:image/png;base64,${plate.image}`}
                          alt={`Biển số ${index + 1} ${plate.aligned ? 'đã' : 'chưa'} căn chỉnh`}
                        />
                        {!plate.aligned ? <p className="alignment-note">Chưa căn chỉnh được</p> : null}
                      </div>
                      <div className="recognition-copy">
                        <p className={plate.text ? 'recognized-text' : undefined}>
                          {plate.text || 'Không đọc được ký tự.'}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="plate-placeholder">Ảnh biển số sau khi phát hiện sẽ hiển thị ở đây.</p>
            )}
          </aside>
        </div>
      </main>
      {notification ? (
        <div
          className={`snackbar${notification.kind === 'error' ? ' error' : ''}`}
          role={notification.kind === 'error' ? 'alert' : 'status'}
        >
          {notification.text}
        </div>
      ) : null}
    </div>
  );
}
