import { describe, expect, it } from 'vitest';
import { contracts } from './contracts';
import { validContractPayloads } from './__fixtures__/contractPayloads';

describe('web/public/data contract schemas', () => {
  it('accept every representative generated JSON payload', () => {
    for (const [name, contract] of Object.entries(contracts)) {
      const result = contract.schema.safeParse(validContractPayloads[name as keyof typeof validContractPayloads]);
      expect(result.success, `${name}: ${result.success ? '' : result.error.message}`).toBe(true);
    }
  });

  it('keeps the schema registry and test fixtures in lockstep', () => {
    expect(Object.keys(validContractPayloads).sort()).toEqual(Object.keys(contracts).sort());
  });
});
