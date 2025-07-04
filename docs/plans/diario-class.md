# Diario Dataclass Implementation Plan

**Status: ADAPTED TO CURRENT PROJECT STATE (2025-06-27)**

Esta é uma adaptação do plano original para implementar a dataclass `Diario` considerando o estado atual do projeto CausaGanha, que já possui:

✅ **Já Implementado:**

- Modern CLI com suporte a `--tribunal` parameter (`causaganha get-urls --tribunal tjro`)
- Modularização tribunal-específica em `src/tribunais/tjro/`
- Sistema de queue unificado com DuckDB
- Pipeline async com Internet Archive integration
- OpenSkill rating system
- Shared database architecture

🔄 **Próximos Passos - Implementação da Dataclass Diario:**

## **Objetivo**

Criar uma abstração `Diario` que unifique o tratamento de documentos judiciais de qualquer tribunal, mantendo a compatibilidade com a arquitetura existente.

---

## **1. Novo arquivo: `src/models/diario.py`**

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from pathlib import Path

@dataclass
class Diario:
    """
    Unified representation of a judicial diary from any tribunal.
    """
    tribunal: str  # 'tjro', 'tjsp', etc.
    data: date
    url: str
    filename: Optional[str] = None
    hash: Optional[str] = None
    pdf_path: Optional[Path] = None
    ia_identifier: Optional[str] = None
    status: str = 'pending'  # pending, downloaded, analyzed, scored
    metadata: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """Human-readable identifier for this diario."""
        return f"{self.tribunal.upper()} - {self.data.isoformat()}"

    @property
    def queue_item(self) -> dict:
        """Convert to job_queue table format for existing database."""
        return {
            'url': self.url,
            'date': self.data.isoformat(),
            'tribunal': self.tribunal,
            'filename': self.filename,
            'metadata': self.metadata,
            'ia_identifier': self.ia_identifier,
            'status': self.status
        }

    @classmethod
    def from_queue_item(cls, queue_row: dict) -> 'Diario':
        """Create Diario from existing job_queue database row."""
        return cls(
            tribunal=queue_row['tribunal'],
            data=date.fromisoformat(queue_row['date']),
            url=queue_row['url'],
            filename=queue_row['filename'],
            ia_identifier=queue_row.get('ia_identifier'),
            status=queue_row.get('status', 'pending'),
            metadata=queue_row.get('metadata', {})
        )
```

---

## **2. Interfaces em `src/models/interfaces.py`**

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from .diario import Diario

class DiarioDiscovery(ABC):
    """Abstract interface for discovering diario URLs from tribunal websites."""

    @abstractmethod
    def get_diario_url(self, target_date: date) -> Optional[str]:
        """Get diario URL for specific date."""
        pass

    @abstractmethod
    def get_latest_diario_url(self) -> Optional[str]:
        """Get URL for the most recent available diario."""
        pass

    @abstractmethod
    def list_diarios_in_range(self, start_date: date, end_date: date) -> List[str]:
        """Get URLs for all diarios in date range."""
        pass

class DiarioDownloader(ABC):
    """Abstract interface for downloading diario PDFs."""

    @abstractmethod
    def download_diario(self, diario: Diario) -> Diario:
        """Download PDF and update diario with local path."""
        pass

    @abstractmethod
    def archive_to_ia(self, diario: Diario) -> Diario:
        """Archive to Internet Archive and update IA identifier."""
        pass

class DiarioAnalyzer(ABC):
    """Abstract interface for analyzing diario content."""

    @abstractmethod
    def extract_decisions(self, diario: Diario) -> List[dict]:
        """Extract judicial decisions from diario PDF."""
        pass
```

---

## **3. Refatoração TJRO: `src/tribunais/tjro/discovery.py`**

```python
import requests
import re
from datetime import date
from typing import Optional, List
from models.interfaces import DiarioDiscovery

class TJRODiscovery(DiarioDiscovery):
    """TJRO-specific diario URL discovery."""

    TJRO_BASE_URL = "https://www.tjro.jus.br/diario_oficial/"

    def get_diario_url(self, target_date: date) -> Optional[str]:
        """Reuse existing logic from downloader.py get_tjro_pdf_url."""
        date_str = target_date.strftime("%Y%m%d")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = requests.get(self.TJRO_BASE_URL, headers=headers, timeout=30)
            response.raise_for_status()

            pdf_match = re.search(
                rf"https://www\.tjro\.jus\.br/novodiario/\d{{4}}/[^\"']*{date_str}[^\"']*\.pdf",
                response.text,
            )

            return pdf_match.group(0) if pdf_match else None

        except requests.RequestException:
            return None

    def get_latest_diario_url(self) -> Optional[str]:
        """Implement latest discovery logic."""
        # Implementation based on existing fetch_latest_tjro_pdf logic
        pass

    def list_diarios_in_range(self, start_date: date, end_date: date) -> List[str]:
        """Get all diario URLs in date range."""
        urls = []
        current = start_date
        while current <= end_date:
            url = self.get_diario_url(current)
            if url:
                urls.append(url)
            current = current.replace(day=current.day + 1)
        return urls
```

---

## **4. Adaptação da CLI existente: `src/cli.py`**

**Integrar com sistema existente:**

```python
# In get_urls command, add Diario integration:

@app.command("get-urls")
def get_urls(
    date: Optional[str] = typer.Option(None, "--date", help="Date in YYYY-MM-DD format"),
    latest: bool = typer.Option(False, "--latest", help="Fetch the latest available PDF"),
    tribunal: str = typer.Option("tjro", "--tribunal", help="Tribunal to fetch from"),
    to_queue: bool = typer.Option(False, "--to-queue", help="Add URLs to queue instead of downloading"),
    as_diario: bool = typer.Option(False, "--as-diario", help="Use new Diario dataclass interface"),
    db_path: Path = typer.Option(Path("data/causaganha.duckdb"), "--db-path"),
):
    """Get URLs and download judicial diarios - supports both legacy and Diario modes."""

    if as_diario:
        # New Diario-based workflow
        from models.diario import Diario
        from tribunais import get_discovery

        discovery = get_discovery(tribunal)

        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            url = discovery.get_diario_url(target_date)
            if url:
                diario = Diario(
                    tribunal=tribunal,
                    data=target_date,
                    url=url,
                    filename=Path(url).name
                )

                if to_queue:
                    # Add Diario to queue
                    _queue_diario(diario)
                    typer.echo(f"✅ Added {diario.display_name} to queue")
                else:
                    # Process immediately
                    _process_diario(diario)
            else:
                typer.echo(f"❌ No diario found for {date}")
    else:
        # Legacy workflow (current implementation)
        # ... existing code ...
```

---

## **5. Registry Pattern: `src/tribunais/__init__.py`**

**Adaptação para usar com arquitetura existente:**

```python
from .tjro.discovery import TJRODiscovery
from .tjro.downloader import TJRODownloader  # Adapter for existing code
from .tjro.analyzer import TJROAnalyzer      # Adapter for existing extractor

# Registry for tribunal-specific implementations
_DISCOVERIES = {
    'tjro': TJRODiscovery,
}

_DOWNLOADERS = {
    'tjro': TJRODownloader,
}

_ANALYZERS = {
    'tjro': TJROAnalyzer,
}

def get_discovery(tribunal: str):
    """Get discovery implementation for tribunal."""
    if tribunal not in _DISCOVERIES:
        raise ValueError(f"Unsupported tribunal: {tribunal}")
    return _DISCOVERIES[tribunal]()

def get_downloader(tribunal: str):
    """Get downloader implementation for tribunal."""
    if tribunal not in _DOWNLOADERS:
        raise ValueError(f"Unsupported tribunal: {tribunal}")
    return _DOWNLOADERS[tribunal]()

def get_analyzer(tribunal: str):
    """Get analyzer implementation for tribunal."""
    if tribunal not in _ANALYZERS:
        raise ValueError(f"Unsupported tribunal: {tribunal}")
    return _ANALYZERS[tribunal]()

def list_supported_tribunals() -> List[str]:
    """Get list of supported tribunals."""
    return list(_DISCOVERIES.keys())
```

---

## **6. Database Integration**

**Estender job_queue existente para suportar Diario:**

```python
# In database.py, add Diario support methods:

def queue_diario(diario: Diario) -> bool:
    """Add Diario to job queue."""
    try:
        conn.execute("""
            INSERT INTO job_queue (url, date, tribunal, filename, metadata, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            diario.url,
            diario.data.isoformat(),
            diario.tribunal,
            diario.filename,
            json.dumps(diario.metadata),
            diario.status
        ])
        return True
    except Exception:
        return False

def get_diarios_by_status(status: str) -> List[Diario]:
    """Get all diarios with specific status."""
    rows = conn.execute("""
        SELECT * FROM job_queue WHERE status = ?
    """, [status]).fetchall()

    return [Diario.from_queue_item(dict(row)) for row in rows]
```

---

## **7. Migration Strategy**

**Implementação gradual mantendo compatibilidade:**

### **Phase 1: Coexistence** ✅ Ready to implement

- Implementar Diario dataclass e interfaces
- Adicionar `--as-diario` flag à CLI existente
- Testar com TJRO usando ambas as abordagens

### **Phase 2: Adoption**

- Migrar comandos CLI para usar Diario por padrão
- Deprecar flags legacy
- Adicionar tribunal validation usando registry

### **Phase 3: Extension**

- Adicionar suporte a novos tribunais (TJSP, TJSC, etc.)
- Implementar discovery automático de tribunais
- Performance optimizations

---

## **8. Testing Strategy**

```python
# tests/test_diario.py
def test_diario_creation():
    diario = Diario(
        tribunal='tjro',
        data=date(2025, 6, 26),
        url='https://tjro.jus.br/test.pdf'
    )
    assert diario.display_name == "TJRO - 2025-06-26"

def test_queue_integration():
    diario = Diario(tribunal='tjro', data=date.today(), url='test')
    queue_item = diario.queue_item
    restored = Diario.from_queue_item(queue_item)
    assert restored.tribunal == diario.tribunal
```

---

## **9. Benefits of This Approach**

✅ **Backward Compatibility**: Mantém toda funcionalidade existente  
✅ **Gradual Migration**: Permite implementação incremental  
✅ **Clean Architecture**: Separa concerns entre discovery, download, analysis  
✅ **Easy Extension**: Novos tribunais só precisam implementar as interfaces  
✅ **Type Safety**: Dataclass provides structure and validation  
✅ **Database Integration**: Works with existing DuckDB schema

---

## **Implementation Priority**

1. **HIGH**: Criar `models/diario.py` e `models/interfaces.py`
2. **HIGH**: Implementar `TJRODiscovery` baseado no código existente
3. **MEDIUM**: Adicionar `--as-diario` flag à CLI
4. **MEDIUM**: Adapter classes para integrar com código existente
5. **LOW**: Migration tools e deprecation warnings

Esta adaptação mantém toda a funcionalidade existente enquanto prepara o terreno para uma arquitetura mais limpa e extensível.
