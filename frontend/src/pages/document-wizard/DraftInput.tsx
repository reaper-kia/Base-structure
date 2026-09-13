import { useCallback, useEffect, useRef, useState } from 'react';
import { useDocumentStore } from '../../shared/store/documentStore';
import { PrimaryButton } from '../../shared/ui/PrimaryButton';
import { SpeechInput } from '../../features/speech/SpeechInput';

const MAX_LENGTH = 20_000;

interface DraftInputProps {
  onNext: () => void;
}

const DEMO_DRAFTS = [
  {
    id: 'vacation',
    title: 'Заявление на отпуск',
    icon: '📋',
    text: `Директору ООО «Ромашка» Петрову П.П.
от менеджера отдела продаж Иванова И.И.

заявленее

прошу предоставить мне отпуск с 10 июня 2025 на 14 дней а то я уже задолбался работать без отдыха и хочу отдохнуть

Иванов`,
  },
  {
    id: 'report',
    title: 'Докладная о перерасчёте',
    icon: '📊',
    text: `Директору ООО «Ромашка» Петрову П.П.
от главного бухгалтера Сидоровой А.В.

Докладная записка
О перерасчёте заработной платы

Довожу до Вашего сведения, что при начислении заработной платы за август 2025 года была допущена ошибка. Сотруднику Иванову И.И. была начислена сумма 45 000 рублей вместо 52 500 рублей.

Прошу дать указание бухгалтерии произвести перерасчёт.

Главный бухгалтер
Сидорова А.В.
05.09.2025`,
  },
  {
    id: 'reference',
    title: 'Справка с места работы',
    icon: '📄',
    text: `Справка

Настоящая справка выдана Сидорову Алексею Петровичу в том, что он действительно работает в ООО «ТехноПром» с 15 марта 2020 года по настоящее время в должности инженера-программиста.

Среднемесячный заработок за последние 12 месяцев составляет 85 000 рублей.

Справка выдана для предъявления по месту требования.

Директор
Козлов Д.В.
12.09.2026`,
  },
  {
    id: 'letter',
    title: 'Коммерческое предложение',
    icon: '✉️',
    text: `Уважаемый Александр Николаевич!

ООО «ТехноПром» обращается к Вам с предложением о сотрудничестве в области поставки программного обеспечения для автоматизации документооборота.

Просим рассмотреть наше коммерческое предложение и дать ответ в течение 10 рабочих дней. Общая стоимость предлагаемого решения составляет 1 250 000 рублей.

С уважением,
Директор ООО «ТехноПром»
Козлов Д.В.`,
  },
  {
    id: 'long',
    title: 'Длинный текст (5000+ символов)',
    icon: '📚',
    text: Array(20)
      .fill(
        'Настоящим докладываю, что в ходе проведения плановой проверки документации было выявлено значительное количество замечаний, требующих немедленного устранения. В частности, речь идёт о систематическом нарушении сроков предоставления отчётности, а также о несоответствии оформления документов установленным требованиям. Прошу принять меры по устранению выявленных недостатков в кратчайшие сроки.'
      )
      .join('\n\n'),
  },
];

export function DraftInput({ onNext }: DraftInputProps) {
  const draft = useDocumentStore((state) => state.draft);
  const setDraft = useDocumentStore((state) => state.setDraft);
  const setDocType = useDocumentStore((state) => state.setDocType);
  const docType = useDocumentStore((state) => state.docType);
  const [pasteError, setPasteError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!docType) {
      setDocType('memo');
    }
  }, [docType, setDocType]);

  const handlePaste = async () => {
    setPasteError(null);
    try {
      const text = await navigator.clipboard.readText();
      setDraft(text.slice(0, MAX_LENGTH));
    } catch {
      setPasteError(
        'Буфер обмена недоступен. Вставьте текст сочетанием Ctrl+V (Cmd+V на Mac) в поле ниже.'
      );
      textareaRef.current?.focus();
    }
  };

  const handleTranscript = useCallback(
    (text: string) => {
      const current = useDocumentStore.getState().draft;
      setDraft(current.trim() ? `${current} ${text}` : text);
    },
    [setDraft]
  );

  const loadDemo = (text: string) => {
    setDraft(text);
    setPasteError(null);
  };

  const canContinue = draft.trim().length >= 10 && draft.length <= MAX_LENGTH;

  return (
    <div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-2">
          <label
            htmlFor="draft-textarea"
            className="block text-xs font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
          >
            Текст черновика
          </label>
          <textarea
            ref={textareaRef}
            id="draft-textarea"
            value={draft}
            onChange={(event) => setDraft(event.target.value.slice(0, MAX_LENGTH))}
            placeholder="Введите или вставьте текст документа... Можно вводить неаккуратно — ИИ исправит орфографию, стиль и структуру."
            rows={12}
            aria-describedby="draft-hint"
            className="w-full outline-none resize-none transition-all py-4 px-4 text-sm leading-relaxed"
            style={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--foreground)',
              fontFamily: 'var(--font-sans)',
            }}
          />
          <div
            id="draft-hint"
            className="flex items-center justify-between mt-1 flex-wrap gap-2"
          >
            <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
              {draft.length} / {MAX_LENGTH} символов
            </span>
            {draft.length > 0 && (
              <button
                type="button"
                onClick={() => setDraft('')}
                aria-label="Очистить поле черновика"
                className="text-xs hover:underline"
                style={{ color: 'var(--muted-foreground)' }}
              >
                Очистить
              </button>
            )}
          </div>

          {pasteError && (
            <div
              role="status"
              className="mt-2 px-3 py-2 text-xs"
              style={{
                background: 'var(--banner-warn-bg)',
                border: '1px solid var(--banner-warn-border)',
                color: 'var(--banner-warn-text)',
                borderRadius: 'var(--radius)',
              }}
            >
              {pasteError}
            </div>
          )}
        </div>

        <div>
          <div
            className="block text-xs font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
          >
            Голосовой ввод
          </div>
          <div className="mb-4">
            <SpeechInput onTranscript={handleTranscript} />
          </div>

          <div
            className="block text-xs font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
          >
            Примеры и инструменты
          </div>
          <div className="space-y-2">
            <button
              type="button"
              onClick={handlePaste}
              aria-label="Вставить текст из буфера обмена"
              className="w-full text-left px-3 py-2.5 text-xs font-semibold transition-all"
              style={{
                background: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: 'var(--foreground)',
              }}
            >
              📋 Вставить из буфера
            </button>
            {DEMO_DRAFTS.map((demo) => (
              <button
                key={demo.id}
                type="button"
                onClick={() => loadDemo(demo.text)}
                aria-label={`Загрузить пример: ${demo.title}`}
                className="w-full text-left px-3 py-2.5 text-xs transition-all"
                style={{
                  background: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  color: 'var(--muted-foreground)',
                }}
              >
                <span className="mr-1.5 inline-flex">{demo.icon}</span>
                <span className="font-medium">{demo.title}</span>
                <span
                  className="block mt-0.5 line-clamp-2 opacity-70"
                  style={{ fontSize: '0.68rem' }}
                >
                  {demo.text.substring(0, 60)}…
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <PrimaryButton
          disabled={!canContinue}
          onClick={onNext}
          aria-label={
            !canContinue
              ? 'Введите минимум 10 символов, чтобы продолжить'
              : 'Перейти к выбору типа и шаблона'
          }
        >
          Далее: выбор типа и шаблона →
        </PrimaryButton>
      </div>
    </div>
  );
}