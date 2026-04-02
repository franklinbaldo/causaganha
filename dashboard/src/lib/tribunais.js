/**
 * Brazilian tribunals organized by branch of justice.
 * Mirrors src/djen_backup/tribunais.py — keep in sync.
 */

export const TRIBUNAL_GROUPS = [
  {
    name: "Tribunais Superiores",
    tribunals: ["STF", "STJ", "TST", "TSE", "STM", "CNJ"],
  },
  {
    name: "Justica Federal",
    tribunals: ["CJF", "PJeCor", "SEEU", "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"],
  },
  {
    name: "Justica Estadual",
    tribunals: [
      "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDFT", "TJES", "TJGO",
      "TJMA", "TJMG", "TJMS", "TJMT", "TJPA", "TJPB", "TJPE", "TJPI", "TJPR",
      "TJRJ", "TJRN", "TJRO", "TJRR", "TJRS", "TJSC", "TJSE", "TJSP", "TJTO",
    ],
  },
  {
    name: "Justica Militar Estadual",
    tribunals: ["TJMMG", "TJMRS", "TJMSP"],
  },
  {
    name: "Justica do Trabalho",
    tribunals: [
      "TRT1", "TRT2", "TRT3", "TRT4", "TRT5", "TRT6", "TRT7", "TRT8", "TRT9",
      "TRT10", "TRT11", "TRT12", "TRT13", "TRT14", "TRT15", "TRT16", "TRT17",
      "TRT18", "TRT19", "TRT20", "TRT21", "TRT22", "TRT23", "TRT24",
    ],
  },
  {
    name: "Justica Eleitoral",
    tribunals: [
      "TRE-AC", "TRE-AL", "TRE-AM", "TRE-AP", "TRE-BA", "TRE-CE", "TRE-DF",
      "TRE-ES", "TRE-GO", "TRE-MA", "TRE-MG", "TRE-MS", "TRE-MT", "TRE-PA",
      "TRE-PB", "TRE-PE", "TRE-PI", "TRE-PR", "TRE-RJ", "TRE-RN", "TRE-RO",
      "TRE-RR", "TRE-RS", "TRE-SC", "TRE-SE", "TRE-SP", "TRE-TO",
    ],
  },
];

// Flat list for backward compatibility
export const TRIBUNAIS = TRIBUNAL_GROUPS.flatMap(g => g.tribunals);
