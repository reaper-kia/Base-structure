import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DevPanel } from '../DevPanel';
import { mockApi } from '../../../shared/api/mock';

describe('DevPanel', () => {
  beforeEach(async () => {
    await mockApi.setAiForceFailure(false);
  });

  afterEach(async () => {
    await mockApi.setAiForceFailure(false);
  });

  it('восстанавливает положение тумблера из dev/state', async () => {
    await mockApi.setAiForceFailure(true);

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
      const state = await mockApi.getDevState();
      expect(state.ai_force_failure).toBe(true);
    });
  });
});