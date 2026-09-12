import { describe, expect, it } from 'vitest';
import { encodePcm16Wav } from './audio';

describe('encodePcm16Wav', () => {
  it('создаёт моно PCM WAV с частотой 16 кГц', async () => {
    const wav = encodePcm16Wav(new Float32Array([-1, 0, 1]));
    const bytes = await new Promise<ArrayBuffer>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as ArrayBuffer);
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(wav);
    });
    const view = new DataView(bytes);

    expect(wav.type).toBe('audio/wav');
    expect(wav.size).toBe(50);
    expect(view.getUint32(24, true)).toBe(16_000);
    expect(view.getUint16(22, true)).toBe(1);
    expect(view.getUint16(34, true)).toBe(16);
    expect(view.getInt16(44, true)).toBe(-32_768);
    expect(view.getInt16(46, true)).toBe(0);
    expect(view.getInt16(48, true)).toBe(32_767);
  });
});