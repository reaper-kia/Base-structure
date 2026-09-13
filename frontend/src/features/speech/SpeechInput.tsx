import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiClient } from '../../shared/api/client';
import { convertAudioBlobToWav } from '../../shared/lib/audio';

const MAX_RECORDING_MS = 179_000;
const LIMIT_WARNING_MS = 30_000;
// Чуть больше серверного лимита (150 с), но меньше proxy_read_timeout Nginx (180 с).
const STT_REQUEST_TIMEOUT_MS = 160_000;

type Phase = 'idle' | 'recording' | 'stopping' | 'transcribing';

interface SttResponse {
  text: string;
  duration_seconds: number;
  model: string;
}

interface SpeechInputProps {
  onTranscript: (text: string) => void;
}

function stopTracks(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof DOMException && error.name === 'TimeoutError') {
    return 'Распознавание заняло слишком много времени. Попробуйте ещё раз.';
  }
  if (error instanceof DOMException && error.name === 'NotAllowedError') {
    return 'Разрешите доступ к микрофону в настройках браузера.';
  }
  return 'Не удалось распознать запись. Попробуйте ещё раз.';
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export function SpeechInput({ onTranscript }: SpeechInputProps) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const tickRef = useRef<number | null>(null);
  const startedAtRef = useRef<number>(0);
  const requestRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  const insecure = typeof window !== 'undefined' && !window.isSecureContext;

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const clearTick = useCallback(() => {
    if (tickRef.current !== null) {
      window.clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const transcribe = useCallback(
    async (recorder: MediaRecorder) => {
      clearTimer();
      clearTick();
      stopTracks(streamRef.current);
      streamRef.current = null;

      if (!mountedRef.current) return;

      setPhase('transcribing');
      setMessage('Распознаю запись…');
      setHasError(false);

      try {
        const recordedAudio = new Blob(chunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });
        chunksRef.current = [];

        if (recordedAudio.size === 0) {
          throw new Error('empty recording');
        }

        const wav = await convertAudioBlobToWav(recordedAudio);
        if (!mountedRef.current) return;

        const form = new FormData();
        form.append('audio', wav, 'recording.wav');

        const request = new AbortController();
        requestRef.current = request;
        let requestTimedOut = false;
        const requestTimeout = window.setTimeout(() => {
          requestTimedOut = true;
          request.abort();
        }, STT_REQUEST_TIMEOUT_MS);

        let result: SttResponse;
        try {
          result = await apiClient.postForm<SttResponse>(
            '/stt',
            form,
            request.signal
          );
        } catch (error) {
          if (requestTimedOut) {
            throw new DOMException('STT request timed out', 'TimeoutError');
          }
          throw error;
        } finally {
          window.clearTimeout(requestTimeout);
        }

        if (!mountedRef.current) return;

        const text = result.text.trim();

        if (text) {
          onTranscript(text);
          setMessage(
            `Добавлена расшифровка записи (${result.duration_seconds.toFixed(1)} с).`
          );
        } else {
          setMessage('Речь не распознана. Попробуйте говорить ближе к микрофону.');
        }
      } catch (error) {
        if (!mountedRef.current) return;
        setHasError(true);
        setMessage(errorMessage(error));
      } finally {
        requestRef.current = null;
        if (mountedRef.current) {
          recorderRef.current = null;
          setPhase('idle');
        }
      }
    },
    [clearTimer, clearTick, onTranscript]
  );

  const startRecording = useCallback(async () => {
    setMessage(null);
    setHasError(false);

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setHasError(true);
      setMessage('Этот браузер не поддерживает запись с микрофона.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      if (!mountedRef.current) {
        stopTracks(stream);
        streamRef.current = null;
        return;
      }

      const recorder = new MediaRecorder(stream);

      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        void transcribe(recorder);
      };
      recorder.onerror = () => {
        if (!mountedRef.current) return;
        clearTimer();
        clearTick();
        recorder.onstop = null;
        if (recorder.state !== 'inactive') recorder.stop();
        stopTracks(streamRef.current);
        streamRef.current = null;
        recorderRef.current = null;
        chunksRef.current = [];
        setHasError(true);
        setMessage('Ошибка записи с микрофона.');
        setPhase('idle');
      };

      recorder.start(1_000);
      setPhase('recording');
      setElapsedMs(0);
      startedAtRef.current = Date.now();
      tickRef.current = window.setInterval(() => {
        setElapsedMs(Date.now() - startedAtRef.current);
      }, 1_000);
      setMessage('Идёт запись. Максимальная длительность — 3 минуты.');
      timerRef.current = window.setTimeout(() => {
        if (recorder.state !== 'inactive') {
          setPhase('stopping');
          recorder.stop();
        }
      }, MAX_RECORDING_MS);
    } catch (error) {
      stopTracks(streamRef.current);
      streamRef.current = null;
      recorderRef.current = null;
      setHasError(true);
      setMessage(errorMessage(error));
      setPhase('idle');
    }
  }, [clearTimer, clearTick, transcribe]);

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === 'inactive') return;

    clearTick();
    setPhase('stopping');
    setMessage('Завершаю запись…');
    recorder.stop();
  }, [clearTick]);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      clearTimer();
      clearTick();
      requestRef.current?.abort();
      const recorder = recorderRef.current;
      if (recorder) recorder.onstop = null;
      if (recorder && recorder.state !== 'inactive') recorder.stop();
      stopTracks(streamRef.current);
    };
  }, [clearTimer, clearTick]);

  useEffect(() => {
    if (insecure) {
      setHasError(true);
      setMessage('Голосовой ввод доступен только по HTTPS.');
    }
  }, [insecure]);

  const busy = phase === 'stopping' || phase === 'transcribing';
  const recording = phase === 'recording';
  const nearLimit =
    recording && elapsedMs >= MAX_RECORDING_MS - LIMIT_WARNING_MS;

  const buttonColors = recording
    ? {
        background: 'var(--banner-error-bg)',
        border: '1px solid var(--banner-error-border)',
        color: 'var(--banner-error-text)',
      }
    : busy
      ? {
          background: 'var(--muted)',
          border: '1px solid var(--border)',
          color: 'var(--muted-foreground)',
        }
      : {
          background: 'var(--chip-found-bg)',
          border: '1px solid var(--chip-found-border)',
          color: 'var(--chip-found-text)',
        };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <button
        type="button"
        data-testid="speech-button"
        onClick={recording ? stopRecording : startRecording}
        disabled={busy || insecure}
        aria-pressed={recording}
        className="transition-all"
        style={{
          padding: '8px 16px',
          fontSize: '14px',
          borderRadius: 'var(--radius)',
          cursor: busy ? 'wait' : insecure ? 'not-allowed' : 'pointer',
          opacity: busy ? 0.7 : 1,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          ...buttonColors,
        }}
      >
        {recording && (
          <span
            aria-hidden="true"
            data-testid="speech-dot"
            className="animate-pulse"
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: 'var(--banner-error-text)',
              flexShrink: 0,
            }}
          />
        )}
        {recording && (
          <span
            data-testid="speech-timer"
            style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: nearLimit ? 700 : 500,
              ...(nearLimit
                ? {
                    background: 'var(--banner-error-border)',
                    padding: '0 4px',
                    borderRadius: 4,
                  }
                : {}),
            }}
          >
            {formatElapsed(elapsedMs)}
          </span>
        )}
        {recording
          ? 'Остановить диктовку'
          : phase === 'transcribing'
            ? 'Распознаю…'
            : phase === 'stopping'
              ? 'Завершаю запись…'
              : 'Начать диктовку'}
      </button>

      {nearLimit && (
        <span
          role="status"
          style={{ color: 'var(--banner-warn-text)', fontSize: '12px' }}
        >
          Приближается лимит — запись остановится автоматически через несколько
          секунд.
        </span>
      )}

      {message && (
        <span
          role={hasError ? 'alert' : 'status'}
          aria-live="polite"
          style={{
            color: hasError ? 'var(--banner-error-text)' : 'var(--muted-foreground)',
            fontSize: '13px',
          }}
        >
          {message}
        </span>
      )}
    </div>
  );
}