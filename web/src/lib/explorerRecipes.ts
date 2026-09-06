export type ExplorerRecipeParams = {
  startDate?: string;
  endDate?: string;
  cnj?: string;
};

export type ExplorerRecipe = {
  key: string;
  label: string;
  description: string;
  sql: string;
  requiredFiles: string[];
  missingInput?: 'period' | 'cnj' | null;
};

type PathBuilder = (fileName: string) => string;

function sqlDate(value: string | undefined): string | null {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  return value;
}

export function normalizeCnj(value: string | undefined): string | null {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 20 ? digits : null;
}

export function buildExplorerRecipes(
  path: PathBuilder,
  params: ExplorerRecipeParams = {},
): ExplorerRecipe[] {
  const startDate = sqlDate(params.startDate);
  const endDate = sqlDate(params.endDate);
  const cnj = normalizeCnj(params.cnj);
  const comunicacoes = path('comunicacoes.parquet');
  const advogados = path('advogados.parquet');
  const vinculos = path('comunicacao_advogados.parquet');

  return [
    {
      key: 'por-orgao',
      label: 'Comunicações por órgão',
      description: 'Conta as comunicações por órgão julgador no dataset selecionado.',
      requiredFiles: ['comunicacoes.parquet'],
      sql: `SELECT nome_orgao, COUNT(*) AS total\nFROM read_parquet('${comunicacoes}')\nGROUP BY nome_orgao\nORDER BY total DESC\nLIMIT 20`,
    },
    {
      key: 'por-periodo',
      label: 'Comunicações por período',
      description: 'Recorta as comunicações entre duas datas e mantém o SQL completo visível.',
      requiredFiles: ['comunicacoes.parquet'],
      missingInput: startDate && endDate ? null : 'period',
      sql: startDate && endDate
        ? `SELECT data_disponibilizacao, numero_processo, nome_orgao\nFROM read_parquet('${comunicacoes}')\nWHERE data_disponibilizacao BETWEEN DATE '${startDate}' AND DATE '${endDate}'\nORDER BY data_disponibilizacao DESC\nLIMIT 200`
        : '-- Informe data inicial e final para gerar esta receita.',
    },
    {
      key: 'por-cnj',
      label: 'Comunicações por CNJ',
      description: 'Localiza comunicações de um processo usando somente os 20 dígitos normalizados do CNJ.',
      requiredFiles: ['comunicacoes.parquet'],
      missingInput: cnj ? null : 'cnj',
      sql: cnj
        ? `SELECT *\nFROM read_parquet('${comunicacoes}')\nWHERE regexp_replace(numero_processo, '[^0-9]', '', 'g') = '${cnj}'\nORDER BY data_disponibilizacao DESC\nLIMIT 200`
        : '-- Informe um número CNJ válido (20 dígitos) para gerar esta receita.',
    },
    {
      key: 'por-data-orgao',
      label: 'Contagem por data e órgão',
      description: 'Mostra o volume diário por órgão para auditoria rápida da distribuição.',
      requiredFiles: ['comunicacoes.parquet'],
      sql: `SELECT data_disponibilizacao, nome_orgao, COUNT(*) AS total\nFROM read_parquet('${comunicacoes}')\nGROUP BY data_disponibilizacao, nome_orgao\nORDER BY data_disponibilizacao DESC, total DESC\nLIMIT 200`,
    },
    {
      key: 'advogados-ativos',
      label: 'Advogados mais ativos',
      description: 'Cruza advogados com vínculos de comunicação para ranquear por volume.',
      requiredFiles: ['advogados.parquet', 'comunicacao_advogados.parquet'],
      sql: `SELECT nome, numero_oab, uf_oab, COUNT(*) AS comunicacoes\nFROM read_parquet('${advogados}') a\nJOIN read_parquet('${vinculos}') ca\n  ON a.id = ca.advogado_id\nGROUP BY nome, numero_oab, uf_oab\nORDER BY comunicacoes DESC\nLIMIT 20`,
    },
    {
      key: 'processos-distintos',
      label: 'Processos distintos',
      description: 'Conta processos únicos nas comunicações.',
      requiredFiles: ['comunicacoes.parquet'],
      sql: `SELECT COUNT(DISTINCT numero_processo) AS processos\nFROM read_parquet('${comunicacoes}')`,
    },
    {
      key: 'schema',
      label: 'Schema de comunicações',
      description: 'Inspeciona as colunas de comunicações sem carregar linhas.',
      requiredFiles: ['comunicacoes.parquet'],
      sql: `DESCRIBE SELECT * FROM read_parquet('${comunicacoes}') LIMIT 0`,
    },
    {
      key: 'proveniencia',
      label: 'Auditar arquivo de origem',
      description: 'Expõe o caminho remoto que o DuckDB está lendo e quantas linhas vieram dele.',
      requiredFiles: ['comunicacoes.parquet'],
      sql: `SELECT filename AS arquivo_ia_url, COUNT(*) AS linhas\nFROM read_parquet('${comunicacoes}', filename = true)\nGROUP BY filename`,
    },
  ];
}

export function recipeIsAvailable(recipe: ExplorerRecipe, availableFileNames: Iterable<string>): boolean {
  const available = new Set(availableFileNames);
  return recipe.requiredFiles.every((fileName) => available.has(fileName));
}
