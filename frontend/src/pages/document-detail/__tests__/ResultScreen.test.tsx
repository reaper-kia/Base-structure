import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ResultScreen } from '../ResultScreen';
import { useDocumentStore } from '../../../shared/store/documentStore';
import type { DocumentState } from '../../../shared/api/types';

function makeDocument(status: 'processed' | 'degraded' = 'processed'): DocumentState {
  return {
    id: 'doc-1',
    status,
    stage: null,
    doc_type: 'memo',
    template_id: 'classic',
    draft: 'заявленее',
    improved_text: 'заявление',
    changes: [
      {
        type: 'spelling',
        from: 'заявленее',
        to: 'заявление',
      },
    ],
    requisites: [],
    fact_guard: {
      verdict: 'clean',
      preserved: ['факт'],
      lost: [],
      added: [],
      source_count: 1,
      preserved_count: 1,
    },
    is_fallback: false,
    error: null,
  };
}

describe('ResultScreen', () => {
  it('при degraded показывает плашку резервного режима', () => {
    render(
      <MemoryRouter>
        <ResultScreen document={makeDocument('degraded')} />
      </MemoryRouter>
    );

    expect(
      screen.getByText('Обработано в резервном режиме: ИИ-компонент был недоступен.')
    ).toBeInTheDocument();
  });

  it('показывает ссылку на trace', () => {
    render(
      <MemoryRouter>
        <ResultScreen document={makeDocument()} />
      </MemoryRouter>
    );

    expect(screen.getByText('Смотреть технический trace')).toHaveAttribute(
      'href',
      '/trace/doc-1'
    );
  });

    it('показывает плашку запасного шаблона уровнем информация', () => {
    useDocumentStore.setState({
      renderFallback: 'Шаблон «modern» повреждён, применён «classic»',
    });

    render(
      <MemoryRouter>
        <ResultScreen document={makeDocument()} />
      </MemoryRouter>
    );

    expect(
      screen.getByText('Шаблон «modern» повреждён, применён «classic»')
    ).toBeInTheDocument();

    useDocumentStore.setState({ renderFallback: null });
  });
});