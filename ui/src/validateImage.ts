const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_TYPES: Record<string, true> = { 'image/jpeg': true, 'image/png': true, 'image/webp': true };

export function validateImage(file: File): string | null {
  if (!ALLOWED_TYPES[file.type]) return 'Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.';
  if (file.size > MAX_FILE_SIZE) return 'Ảnh phải có dung lượng tối đa 10 MB.';
  return null;
}
