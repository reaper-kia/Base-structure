import { Banner } from '../../shared/ui/Banner';

// Причины приходят от ml_service (contracts/llm_contract.md §2) и доезжают
// сюда через reason_code документа. «ИИ не сработал» и «модель выдумала
// факты» — разные вещи, и пользователю важно видеть, какая именно.
const REASON_TEXTS: Record<string, string> = {
  model_unavailable: 'ИИ-компонент недоступен.',
  llm_unavailable: 'ИИ-компонент недоступен.',
  schema_invalid: 'Модель вернула ответ в неверном формате.',
  llm_invalid_response: 'Модель вернула ответ в неверном формате.',
  facts_unverified: 'Модель добавила сведения, которых не было в черновике.',
  empty_text: 'Модель вернула пустой текст.',
};

interface DegradedBannerProps {
  reason?: string | null;
}

export function DegradedBanner({ reason }: DegradedBannerProps) {
  const cause = (reason && REASON_TEXTS[reason]) || 'ИИ-компонент был недоступен.';

  return (
    <Banner level="warning">
      Обработано в резервном режиме: {cause} Текст приведён к деловому виду
      по правилам без участия модели, ни один факт не изменён. Документ можно
      скачать или повторить обработку, когда ИИ снова будет доступен.
    </Banner>
  );
}