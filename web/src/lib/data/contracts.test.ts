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

  it('accepts a site_status payload predating pending_real_max_age_hours', () => {
    // Regression: .github/workflows/cobogo-core-adoption-capture.yml pins a
    // static site-status.json fixture that isn't regenerated per-field — a
    // newly required field there breaks that workflow's build, not just
    // this repo's own contract. The field must stay optional (rollout-safe).
    const { pending_real_max_age_hours: _omit, ...djenWithoutNewField } =
      validContractPayloads.site_status.sources.djen;
    const legacyPayload = {
      ...validContractPayloads.site_status,
      sources: { djen: djenWithoutNewField },
    };

    const result = contracts.site_status.schema.safeParse(legacyPayload);

    expect(result.success, result.success ? '' : result.error.message).toBe(true);
  });
});
