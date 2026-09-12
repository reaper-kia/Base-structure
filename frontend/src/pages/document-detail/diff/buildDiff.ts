import { diffWordsWithSpace } from 'diff';
import type { ChangeItem, ChangeType } from '../../../shared/api/types';

export type DiffSegmentKind = 'equal' | 'insert' | 'delete';

export type SegmentChangeType = ChangeType | 'neutral';

export interface DiffSegment {
  id: string;
  kind: DiffSegmentKind;
  text: string;
  changeType?: SegmentChangeType;
  before?: string;
  after?: string;
}

export interface BuiltDiff {
  left: DiffSegment[];
  right: DiffSegment[];
}

function normalize(value: string): string {
  return value.trim().replace(/\s+/g, ' ').toLowerCase();
}

function classifyChange(
  before: string,
  after: string,
  changes: ChangeItem[]
): SegmentChangeType {
  const normalizedBefore = normalize(before);
  const normalizedAfter = normalize(after);

  const exact = changes.find(
    (change) =>
      normalize(change.from) === normalizedBefore &&
      normalize(change.to) === normalizedAfter
  );

  if (exact) return exact.type;

  const partial = changes.find((change) => {
    const from = normalize(change.from);
    const to = normalize(change.to);

    const fromMatches =
      from.length === 0 ||
      normalizedBefore.includes(from) ||
      from.includes(normalizedBefore);

    const toMatches =
      to.length === 0 ||
      normalizedAfter.includes(to) ||
      to.includes(normalizedAfter);

    return fromMatches && toMatches;
  });

  return partial?.type ?? 'neutral';
}

function makeEqualSegment(id: number, text: string): DiffSegment {
  return {
    id: `equal-${id}`,
    kind: 'equal',
    text,
  };
}

function makeDeleteSegment(
  id: number,
  text: string,
  changeType: SegmentChangeType,
  after: string
): DiffSegment {
  return {
    id: `delete-${id}`,
    kind: 'delete',
    text,
    changeType,
    before: text,
    after,
  };
}

function makeInsertSegment(
  id: number,
  text: string,
  changeType: SegmentChangeType,
  before: string
): DiffSegment {
  return {
    id: `insert-${id}`,
    kind: 'insert',
    text,
    changeType,
    before,
    after: text,
  };
}

export function buildDiff(
  draft: string,
  improvedText: string,
  changes: ChangeItem[]
): BuiltDiff {
  const rawParts = diffWordsWithSpace(draft, improvedText);
  const left: DiffSegment[] = [];
  const right: DiffSegment[] = [];

  let id = 0;

  for (let index = 0; index < rawParts.length; index += 1) {
    const part = rawParts[index];

    if (!part.added && !part.removed) {
      const segment = makeEqualSegment(id, part.value);
      left.push(segment);
      right.push(segment);
      id += 1;
      continue;
    }

    if (part.removed) {
      const next = rawParts[index + 1];

      if (next?.added) {
        const changeType = classifyChange(part.value, next.value, changes);

        left.push(makeDeleteSegment(id, part.value, changeType, next.value));
        right.push(makeInsertSegment(id, next.value, changeType, part.value));

        index += 1;
        id += 1;
        continue;
      }

      const changeType = classifyChange(part.value, '', changes);
      left.push(makeDeleteSegment(id, part.value, changeType, ''));
      id += 1;
      continue;
    }

    if (part.added) {
      const changeType = classifyChange('', part.value, changes);
      right.push(makeInsertSegment(id, part.value, changeType, ''));
      id += 1;
    }
  }

  return { left, right };
}