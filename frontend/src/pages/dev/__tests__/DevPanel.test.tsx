import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DevPanel } from '../DevPanel';
import { api } from '../../../shared/api';

describe('DevPanel', () => {
  beforeEach(async () => {
    await api.setAiForceFailure(false);
  });

  afterEach(async () => {
    await api.setAiForceFailure(false);
  });

  it('восстанавливает положение тумблера из dev/state', async () => {
    await api.setAiForceFailure(true);

    render(<DevPanel />);

    await waitFor(() => {
      expect(screen.getByTestId('break-ai-toggle')).toBeChecked();
    });
  });

  it('тумблер переключает режим отказа ИИ', async () => {
    render(<DevPanel />);

    await waitFor(() => {
      expect(screen.getByTestId('break-ai-toggle')).not.toBeChecked();
    });

    fireEvent.click(screen.getByTestId('break-ai-toggle'));

    await waitFor(async () => {
      const state = await api.getDevState();
      expect(state.ai_force_failure).toBe(true);
    });
  });
});