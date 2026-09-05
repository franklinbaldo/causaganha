import { describe, expect, it } from 'vitest';
import { ProcessoConsultarSchema } from './processoConsultar.gen';

describe('ProcessoConsultar shared semantic core — absence', () => {
  it('accepts a valid process absent from every published source', () => {
    const result = ProcessoConsultarSchema.parse({
      type: 'Processo',
      nr_processo: '11111111111111111111',
      nr_processo_mascara: '1111111-11.1111.1.11.1111',
      encontrado: false,
      fontes_presentes: [],
      djen_id: null,
      juris_id: null,
      stj_id: null,
      datajud_id: null,
      documentos_truncados: false,
      dataset_gerado_em: null,
      avisos: ['relatorio_indisponivel'],
      djen: null,
      juris: null,
      stj: null,
      datajud: null,
      cobertura_dataset: [],
      documentos: [],
    });

    expect(result.encontrado).toBe(false);
    expect(result.dataset_gerado_em).toBeNull();
    expect(result.djen_id).toBeNull();
    expect(result.juris_id).toBeNull();
    expect(result.stj_id).toBeNull();
    expect(result.datajud_id).toBeNull();
  });
});
