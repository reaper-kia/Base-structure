import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TimeoutScreen } from '../TimeoutScreen';

describe('FE-15: экран таймаута', () => {
  it('предлагает продолжать ждать и не предлагает слепой повтор', () => {
    const onContinue = vi.fn();
    render(<TimeoutScreen onContinue={onContinue} />);

    expect(screen.getByText('Продолжить ждать')).toBeInTheDocument();
    expect(screen.queryByText('Повторить')).not.toBeInTheDocument();
  });
});