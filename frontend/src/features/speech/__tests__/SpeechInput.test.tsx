import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SpeechInput } from '../SpeechInput';

class FakeMediaRecorder {
  state: string = 'recording';
  mimeType = 'audio/webm';
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: (() => void) | null = null;
  start() {}
  stop() {
    this.state = 'inactive';
    this.onstop?.();
  }
}

function setSecure(value: boolean) {
  Object.defineProperty(window, 'isSecureContext', {
    value,
    configurable: true,
  });
}

function mockMedia() {
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [] }) },
    configurable: true,
  });
  vi.stubGlobal('MediaRecorder', FakeMediaRecorder);
}

describe('SpeechInput', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    setSecure(true);
  });

  it('вне HTTPS показывает конкретное сообщение и блокирует кнопку', () => {
    setSecure(false);

    render(<SpeechInput onTranscript={() => {}} />);

    expect(
      screen.getByText('Голосовой ввод доступен только по HTTPS.')
    ).toBeInTheDocument();
    expect(screen.getByTestId('speech-button')).toBeDisabled();
  });

  it('во время записи показывает индикатор и таймер, секунды тикают', async () => {
    vi.useFakeTimers();
    setSecure(true);
    mockMedia();

    render(<SpeechInput onTranscript={() => {}} />);
    fireEvent.click(screen.getByTestId('speech-button'));

    await vi.advanceTimersByTimeAsync(1_000);

    expect(screen.getByTestId('speech-button')).toHaveAttribute(
      'aria-pressed',
      'true'
    );
    expect(screen.getByTestId('speech-dot')).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(64_000);
    expect(screen.getByTestId('speech-timer')).toHaveTextContent('01:05');
  });

  it('за 30 секунд до лимита предупреждает о приближении конца', async () => {
    vi.useFakeTimers();
    setSecure(true);
    mockMedia();

    render(<SpeechInput onTranscript={() => {}} />);
    fireEvent.click(screen.getByTestId('speech-button'));

    await vi.advanceTimersByTimeAsync(150_000);

    expect(screen.getByText(/Приближается лимит/)).toBeInTheDocument();
  });
});