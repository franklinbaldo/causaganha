import { defineConfig } from "orval";

export default defineConfig({
  djen: {
    input: "../djen.yml",
    output: {
      mode: "single",
      target: "./src/lib/djen-zod.gen.ts",
      client: "zod",
      override: {
        zod: {
          // The live DJEN API returns undeclared extra fields and mixed
          // camelCase/snake_case names not present in the spec. Strict mode
          // would reject every real response, so we keep it off here and rely
          // on normalizePublication() in djen.ts for coercion.
          strict: false,
          coerce: false,
        },
      },
    },
  },
});
