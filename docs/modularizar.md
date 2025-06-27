Segue um **“pseudo-PR”** detalhado, no melhor estilo open source, para implementar essa separação com a dataclass `Diario`, desacoplamento do TJRO e preparação para múltiplos tribunais. Isso é um modelo, não um PR real, mas já serve de roteiro quase “CTRL+C/CTRL+V”.

---

## **Pull Request: Modularização e Generalização com Dataclass Diario**

### **Resumo**

* Cria dataclass `Diario`, centralizando metadados de cada edição.
* Refatora scraper e parser do TJRO para retornar/manipular objetos `Diario`.
* Move toda lógica específica do TJRO para `src/tribunais/tjro/`.
* Define interfaces abstratas para outros tribunais.
* Adapta o core para operar só com objetos `Diario`, preparando terreno para plug de outros tribunais no futuro.
* Atualiza CLI para aceitar argumento `--tribunal`.

---

### **1. Novo arquivo: `src/core/diario.py`**

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

@dataclass
class Diario:
    tribunal: str
    data: date
    url: str
    hash: str
    pdf_path: Optional[str] = None
    processado: bool = False
    extra: dict = field(default_factory=dict)
```

---

### **2. Interfaces em `src/core/interfaces.py`**

```python
from abc import ABC, abstractmethod
from .diario import Diario

class DiarioScraper(ABC):
    @abstractmethod
    def list_diarios(self, year: int) -> list[Diario]:
        pass

    @abstractmethod
    def fetch_pdf(self, diario: Diario) -> Diario:
        """Baixa e salva o PDF, retorna Diario atualizado com pdf_path e hash."""
        pass

class DiarioParser(ABC):
    @abstractmethod
    def parse_pdf(self, diario: Diario) -> list[dict]:
        """Extrai decisões estruturadas do PDF de um Diario."""
        pass
```

---

### **3. Refatoração TJRO: `src/tribunais/tjro/scraper.py`**

```python
import requests
from datetime import datetime
from core.diario import Diario
from core.interfaces import DiarioScraper

class TJROScraper(DiarioScraper):
    def list_diarios(self, year: int) -> list[Diario]:
        url = f"https://www.tjro.jus.br/diario_oficial/list.php?ano={year}"
        r = requests.get(url)
        r.raise_for_status()
        diarios = []
        for item in r.json():
            data_pub = datetime.strptime(item['data'], "%d/%m/%Y").date()
            diarios.append(Diario(
                tribunal='tjro',
                data=data_pub,
                url=item['url'],
                hash=item['sha256'],
                extra={'numero_edicao': item['numero_edicao']}
            ))
        return diarios

    def fetch_pdf(self, diario: Diario) -> Diario:
        r = requests.get(diario.url)
        r.raise_for_status()
        pdf_path = f"data/pdfs/{diario.tribunal}_{diario.data.isoformat()}.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(r.content)
        diario.pdf_path = pdf_path
        # (Ideal: gerar o hash aqui e comparar, para garantir integridade)
        return diario
```

---

### **4. Parser TJRO: `src/tribunais/tjro/parser.py`**

```python
from core.interfaces import DiarioParser

class TJROParser(DiarioParser):
    def parse_pdf(self, diario):
        # Aqui entra o código já existente de parsing LLM, só muda para receber Diario
        pdf_path = diario.pdf_path
        # Chama o LLM, retorna lista de decisões em dicionários
        # Exemplo fake:
        return [
            {'numero_processo': '123', 'polo_ativo': 'A', 'polo_passivo': 'B', 'resultado': 'procedente'}
        ]
```

---

### **5. Atualização do core/pipeline para usar Diario**

**No pipeline principal:**

```python
from tribunais import get_scraper, get_parser

scraper = get_scraper(args.tribunal)
parser = get_parser(args.tribunal)

for diario in scraper.list_diarios(ano=2025):
    if not diario.processado:
        diario = scraper.fetch_pdf(diario)
        decisoes = parser.parse_pdf(diario)
        # Continua processamento (extração, rating, etc)
```

---

### **6. Registro dinâmico de adaptadores em `src/tribunais/__init__.py`**

```python
from .tjro.scraper import TJROScraper
from .tjro.parser import TJROParser

def get_scraper(tribunal):
    if tribunal == 'tjro':
        return TJROScraper()
    # elif tribunal == 'tjsp':
    #     return TJSPscraper()
    raise ValueError("Tribunal não suportado")

def get_parser(tribunal):
    if tribunal == 'tjro':
        return TJROParser()
    # elif tribunal == 'tjsp':
    #     return TJSPParser()
    raise ValueError("Tribunal não suportado")
```

---

### **7. Atualização da CLI**

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--tribunal", default="tjro", help="Tribunal de Justiça")
args = parser.parse_args()

scraper = get_scraper(args.tribunal)
# ...
```

---

### **8. Documentação**

* Atualize README e docs para explicar:

  * Como novos tribunais são adicionados (basta implementar `DiarioScraper` e `DiarioParser`).
  * O core do pipeline só lida com a dataclass `Diario`.
  * Exemplo de extensão/adaptação para outros tribunais.

---

### **9. Testes**

* Ajuste/migre testes para cobrir criação, manipulação e uso de objetos `Diario`.
* Testes do TJRO ficam em `src/tribunais/tjro/tests/`.

---

### **10. Notas Finais**

* **Não precisa migrar tudo de uma vez:** Dá para migrar só scraping e parsing primeiro, e aos poucos ir “enxugando” o core.
* **Generalize o máximo possível:** O pipeline nunca deve depender de estrutura interna específica de tribunal; tudo vem via métodos e campos do `Diario`.

---

## **Resumo**

Esse PR virtual reorganiza a base para um projeto sério e escalável, onde cada edição do diário é um objeto rico, tribunal-agnóstico, e todo novo tribunal só precisa “falar Diario”.
Se quiser, posso detalhar a refatoração de algum arquivo específico do seu projeto real.

Qualquer dúvida, pede o “commit message” detalhado ou exemplos de testes também!
