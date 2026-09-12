import { Banner } from '../../shared/ui/Banner';

const REASON_TEXTS: Record<string, string> = {
  model_unavailable: 'ИИ-компонент недоступен.',
  llm_unavailable: 'ИИ-компонент недоступен.',
  schema_invalid: 'Модель вернула некорректный ответ.',
  llm_invalid_response: 'Модель вернула некорректный ответ.',
  facts_unverified: 'Результат не подтвердил сохранность фактов.',
};

interface DegradedBannerProps {
  reason?: string | null;
}

export function DegradedBanner({ reason }: DegradedBannerProps) {
  const cause = (reason && REASON_TEXTS[reason]) || 'ИИ-компонент был недоступен.';

  return (
    <Banner level="warning">
      Обработано в резервном режиме: {cause} Текст не исправлялся — возвращён
      исходный черновик. Документ можно скачать.
    </Banner>
  );
}