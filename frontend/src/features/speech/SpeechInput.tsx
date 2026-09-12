import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiClient } from '../../shared/api/client';
import { convertAudioBlobToWav } from '../../shared/lib/audio';

const MAX_RECORDING_MS = 179_000;

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
  if (error instanceof DOMException && error.name === 'NotAllowedError') {
    return 'Разрешите доступ к микрофону в настройках браузера.';
  }
  return 'Не удалось распознать запись. Попробуйте ещё раз.';
}

export function SpeechInput({ onTranscript }: SpeechInputProps) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const requestRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const transcribe = useCallback(
    async (recorder: MediaRecorder) => {
      clearTimer();
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
        const result = await apiClient.postForm<SttResponse>('/stt', form, request.signal);

        if (!mountedRef.current) return;

        const text = result.text.trim();

        if (text) {
          onTranscript(text);
          setMessage(`Добавлена расшифровка записи (${result.duration_seconds.toFixed(1)} с).`);
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
    [clearTimer, onTranscript],
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
  }, [clearTimer, transcribe]);

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === 'inactive') return;

    setPhase('stopping');
    setMessage('Завершаю запись…');
    recorder.stop();
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      clearTimer();
      requestRef.current?.abort();
      const recorder = recorderRef.current;
      if (recorder) recorder.onstop = null;
      if (recorder && recorder.state !== 'inactive') recorder.stop();
      stopTracks(streamRef.current);
    };
  }, [clearTimer]);

  const busy = phase === 'stopping' || phase === 'transcribing';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <button
        type="button"
        onClick={phase === 'recording' ? stopRecording : startRecording}
        disabled={busy}
        aria-pressed={phase === 'recording'}
        style={{
          padding: '8px 16px',
          fontSize: '14px',
          backgroundColor: phase === 'recording' ? '#fee2e2' : '#ecfdf5',
          border: `1px solid ${phase === 'recording' ? '#ef4444' : '#10b981'}`,
          borderRadius: '6px',
          cursor: busy ? 'wait' : 'pointer',
          color: phase === 'recording' ? '#991b1b' : '#065f46',
          opacity: busy ? 0.7 : 1,
        }}
      >
        {phase === 'recording'
          ? 'Остановить диктовку'
          : phase === 'transcribing'
            ? 'Распознаю…'
            : phase === 'stopping'
              ? 'Завершаю запись…'
              : 'Начать диктовку'}
      </button>

      {message && (
        <span
          role={hasError ? 'alert' : 'status'}
          aria-live="polite"
          style={{ color: hasError ? '#b91c1c' : '#666', fontSize: '13px' }}
        >
          {message}
        </span>
      )}
    </div>
  );
}