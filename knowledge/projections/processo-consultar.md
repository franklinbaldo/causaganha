---
type: Projection
name: ProcessoConsultar
root: Processo
include:
  - relation: Processo.djen_id
    as: djen
    optional: true
  - relation: Processo.juris_id
    as: juris
    optional: true
  - relation: Processo.stj_id
    as: stj
    optional: true
  - relation: Processo.datajud_id
    as: datajud
    optional: true
  - relation: FonteCobertura.processo_nr
    as: cobertura_dataset
  - relation: DocumentoProcesso.processo_nr
    as: documentos
---

# ProcessoConsultar

Projeção compartilhada do dossiê por CNJ. Ela referencia os contratos-base e não reinlina uma segunda ontologia para MCP ou Web.
