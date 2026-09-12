/**
 * Парсит заголовок Content-Disposition и возвращает имя файла.
 * Работает с форматами:
 *   attachment; filename="name.docx"
 *   attachment; filename=name.docx
 *   attachment; filename*=UTF-8''name.docx
 */
export function parseContentDisposition(
  header: string | null | undefined,
  fallback: string
): string {
  if (!header) return fallback;

  // filename*=UTF-8''... (RFC 5987)
  const starMatch = header.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (starMatch) {
    try {
      return decodeURIComponent(starMatch[1].trim());
    } catch {
      // продолжаем пробовать обычный filename
    }
  }

  // filename="..." или filename=...
  const match = header.match(/filename\s*=\s*"?([^";]+)"?/i);
  if (match) {
    return match[1].trim();
  }

  return fallback;
}