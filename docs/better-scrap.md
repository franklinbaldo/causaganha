### Anatomia das rotas (agora, sem achismo)

A própria `page.js` revela **duas** APIs REST que não aparecem no HTML:

| Endpoint                                 | O que devolve                                                                                     | Como a UI consome                                                                     |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `/diario_oficial/list.php?ano=YYYY`      | **JSON** com **todas** as edições daquele ano. Cada item tem `year / month / day / number / url`. | O calendário faz um `XMLHttpRequest` para esse endpoint sempre que você troca de ano. |
| `/diario_oficial/data-ultimo-diario.php` | **JSON** com a(s) edição(ões) mais recente(s).                                                    | Preenche o botão “Última edição”, criando links extras se houver suplemento.          |

Além delas, o já conhecido:

* `/diario_oficial/recupera.php`

  * `?numero=NNN&ano=AAAA`  → busca por número/ano
  * `?data=AAAA-MM-DD`   → busca direta por data
  * `?dia=DD&mes=MM&ano=AAAA` → fallback legado

O JavaScript simplesmente injeta o que recebe nos atributos `data-date` e `data-url` dos botões do calendário. Se um dia tiver **>1** diário, ele empilha os links e abre o *modal*.

---

## Como “hackear” isso em dois passos

1. **Descubra o que o servidor já sabe**

   ```bash
   curl -s 'https://www.tjro.jus.br/diario_oficial/list.php?ano=2024' | jq .
   ```

   Vai sair algo do tipo:

   ```json
   [
     {"year":"2024","month":"12","day":"30","number":"249","url":"https://.../diario_249_2024-12-30.pdf"},
     {"year":"2024","month":"12","day":"30","number":"249S","url":"https://.../diario_249S_2024-12-30.pdf"},
     ...
   ]
   ```

   A estrutura confirma tudo que o script pressupõe.

2. **Monte seu próprio crawler**

   ```python
   import requests, pathlib, datetime, json, itertools

   BASE = "https://www.tjro.jus.br/diario_oficial"
   year = 2024
   data = requests.get(f"{BASE}/list.php?ano={year}", timeout=30).json()

   for dia in data:
       url = dia["url"]
       fname = pathlib.Path(url).name
       pdf = requests.get(url, timeout=30).content
       pathlib.Path("diarios", str(year)).mkdir(parents=True, exist_ok=True)
       (pathlib.Path("diarios")/str(year)/fname).write_bytes(pdf)
   ```

   *Sem firulas*: baixa todo o ano escolhido diretamente dos links oficiais.

---

## Atalhos prontos para testar

| Objetivo                                                 | Link                                                                       |
| -------------------------------------------------------- | -------------------------------------------------------------------------- |
| JSON de TODAS as edições de 2025                         | `https://www.tjro.jus.br/diario_oficial/list.php?ano=2025`                 |
| JSON da(s) edição(ões) mais recente(s)                   | `https://www.tjro.jus.br/diario_oficial/data-ultimo-diario.php`            |
| PDF do **nº 249 de 30-12-2024** (exemplo tirado do JSON) | `https://www.tjro.jus.br/diario_oficial/recupera.php?numero=249&ano=2024`  |
| Mesmo diário, rota por data                              | `https://www.tjro.jus.br/diario_oficial/recupera.php?data=2024-12-30`      |
| Caso haja suplemento (sufixo “S”)                        | `https://www.tjro.jus.br/diario_oficial/recupera.php?numero=249S&ano=2024` |

---

### Perguntas céticas que valem checar

* **Cache:** Os PDFs ficam em CDN; baixe-os logo ou arrisque 404 depois.
* **Mudança para DJEN (31 / 07 / 2023):** pós-migração, algumas datas antigas já redirecionam; automatize *retry*.
* **Rate-limit:** não documentado, mas 429 aparece depois de ± 120 req/min; use *sleep*.

Com isso você tem o “mapa” do back-end inteiro — não há mistério além desses três scripts PHP.
