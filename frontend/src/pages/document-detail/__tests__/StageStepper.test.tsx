import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StageStepper } from '../StageStepper';

describe('StageStepper', () => {
  it('при llm первая стадия активна, остальные ожидают', () => {
    render(<StageStepper currentStage="llm" />);
    expect(screen.getByTestId('stage-llm')).toHaveAttribute(
      'data-status',
      'active'
    );
    expect(screen.getByTestId('stage-fact_guard')).toHaveAttribute(
      'data-status',
      'pending'
    );
    expect(screen.getByTestId('stage-validation')).toHaveAttribute(
      'data-status',
      'pending'
    );
  });

  it('при fact_guard первая завершена, вторая активна', () => {
    render(<StageStepper currentStage="fact_guard" />);
    expect(screen.getByTestId('stage-llm')).toHaveAttribute(
      'data-status',
      'done'
    );
    expect(screen.getByTestId('stage-fact_guard')).toHaveAttribute(
      'data-status',
      'active'
    );
  });

  it('при validation первые две завершены, третья активна', () => {
    render(<StageStepper currentStage="validation" />);
    expect(screen.getByTestId('stage-llm')).toHaveAttribute(
      'data-status',
      'done'
    );
    expect(screen.getByTestId('stage-fact_guard')).toHaveAttribute(
      'data-status',
      'done'
    );
    expect(screen.getByTestId('stage-validation')).toHaveAttribute(
      'data-status',
      'active'
    );
  });

  it('переключает стадии по мере прихода stage', () => {
    const { rerender } = render(<StageStepper currentStage="llm" />);
    expect(screen.getByTestId('stage-llm')).toHaveAttribute(
      'data-status',
      'active'
    );

    rerender(<StageStepper currentStage="fact_guard" />);
    expect(screen.getByTestId('stage-fact_guard')).toHaveAttribute(
      'data-status',
      'active'
    );

    rerender(<StageStepper currentStage="validation" />);
    expect(screen.getByTestId('stage-validation')).toHaveAttribute(
      'data-status',
      'active'
    );
  });
});