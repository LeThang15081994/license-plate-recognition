import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from './App';

beforeEach(() => {
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => 'blob:preview'),
    revokeObjectURL: vi.fn(),
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it('detects every plate on the selected image without inventing OCR text', async () => {
  const fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      boxes: [
        { x1: 12, y1: 20, x2: 80, y2: 45, confidence: 0.95 },
        { x1: 100, y1: 50, x2: 170, y2: 76, confidence: 0.83 },
      ],
    }),
  });
  vi.stubGlobal('fetch', fetch);
  render(<App />);
  const file = new File(['image'], 'plate.png', { type: 'image/png' });
  fireEvent.change(screen.getByLabelText('Chọn ảnh'), { target: { files: [file] } });
  expect((await screen.findByAltText('Ảnh đã chọn')).getAttribute('src')).toBe('blob:preview');
  const preview = screen.getByAltText('Ảnh đã chọn');
  Object.defineProperties(preview, {
    naturalWidth: { value: 640, configurable: true },
    naturalHeight: { value: 480, configurable: true },
  });
  fireEvent.load(preview);
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Phát hiện biển số' }));
  expect(await screen.findByText('Đã phát hiện 2 biển số.')).toBeTruthy();
  const rects = document.querySelectorAll('svg.plate-boxes rect');
  expect(rects).toHaveLength(2);
  expect(rects[0].getAttribute('x')).toBe('12');
  expect(rects[1].getAttribute('x')).toBe('100');
  expect(fetch).toHaveBeenCalledWith(
    '/api/v1/ocr/detect',
    expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
  );
  expect(screen.getByText(/Chưa có văn bản nhận diện/)).toBeTruthy();
});

it('shows failed detection and clears previous boxes on a new image', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ boxes: [{ x1: 1, y1: 2, x2: 30, y2: 20, confidence: 0.9 }] }),
    })
    .mockRejectedValueOnce(new Error('offline'));
  vi.stubGlobal('fetch', fetch);
  render(<App />);
  const input = screen.getByLabelText('Chọn ảnh');
  fireEvent.change(input, { target: { files: [new File(['first'], 'first.png', { type: 'image/png' })] } });
  const preview = screen.getByAltText('Ảnh đã chọn');
  Object.defineProperties(preview, {
    naturalWidth: { value: 640, configurable: true },
    naturalHeight: { value: 480, configurable: true },
  });
  fireEvent.load(preview);
  fireEvent.click(screen.getByRole('button', { name: 'Phát hiện biển số' }));
  expect(await screen.findByText('Đã phát hiện 1 biển số.')).toBeTruthy();
  expect(document.querySelectorAll('svg.plate-boxes rect')).toHaveLength(1);
  fireEvent.change(input, { target: { files: [new File(['second'], 'second.png', { type: 'image/png' })] } });
  expect(document.querySelectorAll('svg.plate-boxes rect')).toHaveLength(0);
  fireEvent.click(screen.getByRole('button', { name: 'Phát hiện biển số' }));
  expect(await screen.findByRole('alert')).toHaveProperty(
    'textContent',
    'Không thể phát hiện biển số. Vui lòng thử lại.',
  );
});

it('rejects unsupported and oversized images', () => {
  render(<App />);
  const input = screen.getByLabelText('Chọn ảnh');
  fireEvent.change(input, { target: { files: [new File(['bad'], 'notes.txt', { type: 'text/plain' })] } });
  expect(screen.getByRole('alert').textContent).toMatch(/Chỉ hỗ trợ/);
  fireEvent.change(input, {
    target: { files: [new File([new Uint8Array(10 * 1024 * 1024 + 1)], 'large.jpg', { type: 'image/jpeg' })] },
  });
  expect(screen.getByRole('alert').textContent).toMatch(/10 MB/);
  expect(screen.queryByAltText('Ảnh đã chọn')).toBeNull();
});
