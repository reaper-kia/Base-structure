import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DiffView } from '../DiffView';

describe('DiffView', () => {
  it('рендерит side-by-side контейнер', () => {
    render(
      <DiffView
        draft="заявленее"
        improvedText="заявление"
        changes={[]}
      />
    );

    expect(screen.getByTestId('diff-view')).toBeInTheDocument();
    expect(screen.getByText('Черновик')).toBeInTheDocument();
    expect(screen.getByText('Результат')).toBeInTheDocument();
  });

  it('правка типа style получает соответствующий data-атрибут', () => {
    render(
      <DiffView
        draft="а то я уже задолбался"
        improvedText=""
        changes={[
          {
            type: 'style',
            from: 'а то я уже задолбался',
            to: '',
          },
        ]}
      />
    );

    const styleToken = document.querySelector('[data-change-type="style"]');

    expect(styleToken).toBeTruthy();
  });

  it('имеет класс diff-view для мобильной раскладки через CSS', () => {
    render(
      <DiffView
        draft="старый текст"
        improvedText="новый текст"
        changes={[]}
      />
    );

    expect(screen.getByTestId('diff-view')).toHaveClass('diff-view');
  });
});