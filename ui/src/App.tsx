import { useEffect, useRef, useState } from 'react';
import { validateImage } from './validateImage';

interface PlateBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  confidence: number;
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
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [boxes, setBoxes] = useState<PlateBox[]>([]);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);

  useEffect(() => {
    if (preview) return () => URL.revokeObjectURL(preview);
  }, [preview]);
  useEffect(() => () => request.current?.abort(), []);

  function chooseFile(next: File | undefined) {
    if (!next) return;
    const message = validateImage(next);
    setError(message);
    if (message) return;
    request.current?.abort();
    setLoading(false);
    setBoxes([]);
    setImageSize(null);
    setStatus(null);
    setFile(next);
    setPreview(URL.createObjectURL(next));
  }

  async function detectPlates() {
    if (!file) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(null);
    setStatus('Đang phát hiện biển số...');
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
        )
      ) {
        throw new Error('Invalid detection response');
      }
      if (controller.signal.aborted) return;
      setBoxes(data.boxes);
      setStatus(data.boxes.length ? `Đã phát hiện ${data.boxes.length} biển số.` : 'Không tìm thấy biển số.');
    } catch {
      if (!controller.signal.aborted) {
        setStatus(null);
        setError('Không thể phát hiện biển số. Vui lòng thử lại.');
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
          <span className="app-grid" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
          </span>
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
        <section className="upload-card" aria-labelledby="upload-title">
          <h1 id="upload-title">Tải hình ảnh</h1>
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
                        {boxes.map((box, index) => (
                          <rect key={index} x={box.x1} y={box.y1} width={box.x2 - box.x1} height={box.y2 - box.y1} />
                        ))}
                      </svg>
                    ) : null}
                  </span>
                  <span className="preview-actions">
                    <small>{file?.name}</small>
                    <span className="change-photo">Chọn ảnh khác</span>
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
            {status ? (
              <p className="detection-status" role="status">
                {status}
              </p>
            ) : null}
            {error ? (
              <p className="error" role="alert">
                {error}
              </p>
            ) : null}
          </div>
          <div className="result-area" aria-live="polite">
            <h2>Văn bản nhận diện</h2>
            <div className="result-text">
              {file
                ? 'Ảnh đã sẵn sàng. Chưa có văn bản nhận diện — cần kết nối dịch vụ OCR để hiển thị kết quả.'
                : 'Văn bản nhận diện từ ảnh sẽ hiển thị tại đây.'}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
