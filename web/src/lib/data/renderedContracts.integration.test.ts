import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { contracts } from './contracts';

type QueryContract = { name: string; output: string; optional: boolean };
type RenderManifest = { rendered_count: number; contracts: QueryContract[] };

const fixtureRoot = mkdtempSync(join(tmpdir(), 'causaganha-contracts-'));

afterAll(() => rmSync(fixtureRoot, { recursive: true, force: true }));

describe('rendered query contracts', () => {
  it(
    'renders fixture-backed query outputs that match every frontend schema',
    () => {
      execFileSync('uv', ['run', 'python', '../scripts/render_contract_fixture.py', fixtureRoot], {
        cwd: process.cwd(),
        stdio: 'inherit',
      });

      const manifest = JSON.parse(
        readFileSync(join(fixtureRoot, 'query-contracts.json'), 'utf8'),
      ) as RenderManifest;
      const queryByOutput = new Map(manifest.contracts.map((query) => [query.output, query]));
      const frontendByOutput = new Map(
        Object.entries(contracts).map(([name, contract]) => [contract.output, { name, contract }]),
      );
      const dataDir = join(fixtureRoot, 'web/public/data');
      const emittedOutputs = readdirSync(dataDir, { recursive: true })
        .filter((file) => file.endsWith('.json'))
        .map((file) => `data/${file}`);

      expect(manifest.rendered_count).toBe(manifest.contracts.length);

      for (const query of manifest.contracts.filter((contract) => !contract.optional)) {
        expect(
          existsSync(join(fixtureRoot, 'web/public', query.output)),
          `${query.name} must be emitted`,
        ).toBe(true);
      }

      for (const output of emittedOutputs) {
        const frontend = frontendByOutput.get(output);
        expect(frontend, `${output} has no matching frontend contract`).toBeDefined();
        const payload: unknown = JSON.parse(
          readFileSync(join(fixtureRoot, 'web/public', output), 'utf8'),
        );
        const result = frontend!.contract.schema.safeParse(payload);
        expect(
          result.success,
          `${frontend!.name}: ${result.success ? '' : result.error.message}`,
        ).toBe(true);
      }

      expect([...frontendByOutput.keys()].sort()).toEqual([...queryByOutput.keys()].sort());
      expect(emittedOutputs.sort()).toEqual([...queryByOutput.keys()].sort());
    },
    120_000,
  );
});
