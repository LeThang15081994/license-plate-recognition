import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from './App';

const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9CZcAAAAASUVORK5CYII=';

beforeEach(() => {
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => 'blob:preview'),
    revokeObjectURL: vi.fn(),
  });
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it('shows recognized text beside each aligned plate and leaves unreadable plates unlabeled', async () => {
  const fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      boxes: [
        { x1: 12, y1: 20, x2: 80, y2: 45, confidence: 0.95 },
        { x1: 100, y1: 50, x2: 170, y2: 76, confidence: 0.83 },
      ],
      plates: [
        {
          image: png,
          aligned: true,
          text: 'SB2642',
          corners: [
            { x: 13, y: 21, confidence: 0.99 },
            { x: 79, y: 20, confidence: 0.99 },
            { x: 77, y: 44, confidence: 0.99 },
            { x: 12, y: 43, confidence: 0.99 },
          ],
        },
        {
          image: png,
          aligned: false,
          text: '',
          corners: [
            { x: 100, y: 50, confidence: 0.99 },
            { x: 170, y: 50, confidence: 0.99 },
            { x: 170, y: 76, confidence: 0.1 },
            { x: 100, y: 76, confidence: 0.99 },
          ],
        },
      ],
    }),
  });
  vi.stubGlobal('fetch', fetch);
  render(<App />);
  expect(screen.getByRole('button', { name: 'Tải ảnh' })).toBeTruthy();
  const file = new File(['image'], 'plate.png', { type: 'image/png' });
  fireEvent.change(screen.getByLabelText('Chọn ảnh'), { target: { files: [file] } });
  expect((await screen.findByAltText('Ảnh đã chọn')).getAttribute('src')).toBe('blob:preview');
  expect(screen.getByRole('button', { name: 'Chọn ảnh khác' })).toBeTruthy();
  expect(document.querySelector('.dropzone')?.textContent).not.toContain('Chọn ảnh khác');
  const preview = screen.getByAltText('Ảnh đã chọn');
  Object.defineProperties(preview, {
    naturalWidth: { value: 640, configurable: true },
    naturalHeight: { value: 480, configurable: true },
  });
  fireEvent.load(preview);
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Phát hiện biển số' }));
  expect(await screen.findByText('Đã phát hiện 2 biển số.')).toBeTruthy();
  const outlines = document.querySelectorAll('svg.plate-boxes polygon');
  expect(outlines).toHaveLength(1);
  expect(outlines[0].getAttribute('points')).toBe('13,21 79,20 77,44 12,43');
  expect(document.querySelectorAll('svg.plate-boxes rect')).toHaveLength(0);
  const sidebar = screen.getByRole('complementary', { name: 'Ảnh biển số' });
  const images = sidebar.querySelectorAll('img');
  expect(images).toHaveLength(2);
  expect(images[0].getAttribute('src')).toBe(`data:image/png;base64,${png}`);
  expect(images[0].getAttribute('alt')).toBe('Biển số 1 đã căn chỉnh');
  expect(images[1].getAttribute('alt')).toBe('Biển số 2 chưa căn chỉnh');
  expect(screen.getByText('Chưa căn chỉnh được')).toBeTruthy();
  expect(fetch).toHaveBeenCalledWith(
    '/api/v1/ocr/detect',
    expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
  );
  expect(within(sidebar).getByText('SB2642')).toBeTruthy();
  expect(within(sidebar).getByText('Không đọc được ký tự.')).toBeTruthy();
  expect(within(sidebar).queryAllByText('Văn bản nhận diện')).toHaveLength(0);
});

it('shows failed detection and clears previous plate outlines on a new image', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        boxes: [{ x1: 1, y1: 2, x2: 30, y2: 20, confidence: 0.9 }],
        plates: [
          {
            image: png,
            aligned: true,
            text: '51G74372',
            corners: [
              { x: 1, y: 2, confidence: 0.99 },
              { x: 29, y: 2, confidence: 0.99 },
              { x: 28, y: 19, confidence: 0.99 },
              { x: 1, y: 19, confidence: 0.99 },
            ],
          },
        ],
      }),
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
  expect(document.querySelectorAll('svg.plate-boxes polygon')).toHaveLength(1);
  expect(screen.getByRole('complementary', { name: 'Ảnh biển số' }).querySelectorAll('img')).toHaveLength(1);
  fireEvent.change(input, { target: { files: [new File(['second'], 'second.png', { type: 'image/png' })] } });
  expect(document.querySelectorAll('svg.plate-boxes polygon')).toHaveLength(0);
  expect(screen.getByRole('complementary', { name: 'Ảnh biển số' }).querySelectorAll('img')).toHaveLength(0);
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

it('replaces notifications and hides the latest one after six seconds', () => {
  vi.useFakeTimers();
  render(<App />);
  const input = screen.getByLabelText('Chọn ảnh');
  fireEvent.change(input, { target: { files: [new File(['bad'], 'notes.txt', { type: 'text/plain' })] } });
  expect(screen.getByRole('alert').textContent).toMatch(/Chỉ hỗ trợ/);

  act(() => vi.advanceTimersByTime(5999));
  expect(screen.getByRole('alert')).toBeTruthy();
  fireEvent.change(input, {
    target: { files: [new File([new Uint8Array(10 * 1024 * 1024 + 1)], 'large.jpg', { type: 'image/jpeg' })] },
  });
  act(() => vi.advanceTimersByTime(1));
  expect(screen.getByRole('alert').textContent).toMatch(/10 MB/);
  act(() => vi.advanceTimersByTime(5999));
  expect(screen.queryByRole('alert')).toBeNull();
});
