/**
 * Unified loader for the .qmd query contracts (RFC 0009).
 *
 * Two modes, one API:
 *
 * - Build-time (Astro frontmatter / Node): reads web/public/<output> from the
 *   filesystem and validates with the contract's Zod schema.
 *   Missing file → null (pages degrade to EmptyState, as today).
 *   Malformed JSON or schema violation → throws an error naming the contract,
 *   which fails the build (fail-loud, RFC 0007).
 *
 * - Client-side (browser): fetches the same file resolved against Astro's
 *   BASE_URL (same resolution as fetchData.ts — never a bare "/data/..."
 *   absolute path, which would ignore `base: '/causaganha'`).
 *   Any failure (HTTP, malformed JSON, schema violation) → logged + null.
 *
 * `loadContract()` picks the mode automatically. node:fs is imported
 * dynamically inside the build-time branch only, so this module stays safe to
 * import from client code.
 */
import { contracts, type ContractData, type ContractName } from './contracts';

export * from './contracts';

function contractError(name: ContractName, output: string, cause: unknown): Error {
  const detail = cause instanceof Error ? cause.message : String(cause);
  return new Error(
    `Contrato de dados "${name}" inválido (${output}): ${detail}. ` +
      `Verifique web/src/queries/${name}.qmd e a saída de scripts/render_queries.py.`,
  );
}

function parseContract<K extends ContractName>(
  name: K,
  raw: string,
): ContractData<K> {
  const { output, schema } = contracts[name];
  let json: unknown;
  try {
    json = JSON.parse(raw);
  } catch (err) {
    throw contractError(name, output, err);
  }
  const result = schema.safeParse(json);
  if (!result.success) {
    throw contractError(name, output, result.error);
  }
  return result.data as ContractData<K>;
}

/**
 * Build-time loader (Node only). Reads from `<publicDir>/<output>`.
 *
 * @param publicDir Base directory holding the rendered JSON (default:
 *   `./public`, matching Astro's project layout at build time).
 * @returns Parsed, validated data — or null when the file does not exist
 *   (fresh checkout / stub build).
 * @throws When the file exists but is malformed or fails schema validation.
 */
export async function loadContractBuildTime<K extends ContractName>(
  name: K,
  publicDir = './public',
): Promise<ContractData<K> | null> {
  const [{ readFileSync }, { resolve }] = await Promise.all([
    import('node:fs'),
    import('node:path'),
  ]);
  const filePath = resolve(publicDir, contracts[name].output);
  let raw: string;
  try {
    raw = readFileSync(filePath, 'utf-8');
  } catch {
    return null; // missing file → pages keep their EmptyState behaviour
  }
  return parseContract(name, raw);
}

/**
 * Client-side loader (browser). Resolves against Astro's BASE_URL, exactly
 * like fetchData.ts. Validation failures are logged and treated as absence.
 */
export async function loadContractClient<K extends ContractName>(
  name: K,
): Promise<ContractData<K> | null> {
  const BASE: string = import.meta.env.BASE_URL ?? '/';
  const base = BASE.endsWith('/') ? BASE : BASE + '/';
  const url = base + contracts[name].output;
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return parseContract(name, await res.text());
  } catch (err) {
    console.error(`[data] contrato "${name}" falhou no cliente (${url}):`, err);
    return null;
  }
}

/**
 * Unified entry point: build-time (fs) in Node, fetch in the browser.
 */
export async function loadContract<K extends ContractName>(
  name: K,
): Promise<ContractData<K> | null> {
  if (typeof window === 'undefined') {
    return loadContractBuildTime(name);
  }
  return loadContractClient(name);
}
