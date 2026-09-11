import { describe, expect, it } from 'vitest';
import { buildDiff } from '../buildDiff';

describe('buildDiff', () => {
  it('строит diff даже при пустом changes[]', () => {
    const result = buildDiff('заявленее', 'заявление', []);

    expect(result.left.length).toBeGreaterThan(0);
    expect(result.right.length).toBeGreaterThan(0);

    const hasDeleted = result.left.some((segment) => segment.kind === 'delete');
    const hasInserted = result.right.some((segment) => segment.kind === 'insert');

    expect(hasDeleted || hasInserted).toBe(true);
  });

  it('классифицирует правку по changes[]', () => {
    const result = buildDiff('а то я уже задолбался', '', [
      {
        type: 'style',
        from: 'а то я уже задолбался',
        to: '',
      },
    ]);

    const changed = result.left.find((segment) => segment.kind === 'delete');

    expect(changed?.changeType).toBe('style');
  });
});