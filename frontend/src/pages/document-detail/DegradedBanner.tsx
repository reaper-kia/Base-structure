import { Banner } from '../../shared/ui/Banner';

export function DegradedBanner() {
  return (
    <Banner level="warning">
      Обработано в резервном режиме: ИИ-компонент был недоступен.
    </Banner>
  );
}