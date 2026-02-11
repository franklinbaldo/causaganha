# JSONL Progress Tracking

Sistema de rastreamento histórico de progresso usando arquivos JSONL (JSON Lines).

## 📊 Arquivos Gerados

Cada execução de `generate_catalog.py` cria/atualiza:

- `collect-progress.json` - Estado atual (sobrescrito)
- `collect-progress.jsonl` - Histórico completo (append-only)
- `consolidate-progress.json` - Estado atual (sobrescrito)
- `consolidate-progress.jsonl` - Histórico completo (append-only)

## 🔍 Formato JSONL

Cada linha é um objeto JSON completo:

```jsonl
{"oldest_date": "2026-01-14", "newest_date": "2026-02-03", "progress_pct": 1.31, "last_updated": "2026-02-05T08:21:22Z", ...}
{"oldest_date": "2026-01-14", "newest_date": "2026-02-04", "progress_pct": 1.44, "last_updated": "2026-02-05T12:30:00Z", ...}
{"oldest_date": "2026-01-13", "newest_date": "2026-02-04", "progress_pct": 1.57, "last_updated": "2026-02-05T18:45:30Z", ...}
```

**Vantagens:**
- ✅ Cada linha é válida JSON independente
- ✅ Append-only = nunca perde dados
- ✅ Trivial parsear: `cat file.jsonl | jq .`
- ✅ Comparação fácil: `tail -2 file.jsonl`

## 💻 Exemplos de Uso

### 1. Comparar Última vs Anterior

```bash
# Bash
tail -2 catalog/collect-progress.jsonl | jq -s '
  {
    previous: .[0],
    current: .[1],
    delta_pct: (.[1].progress_pct - .[0].progress_pct),
    time_diff_hours: ((.[1].last_updated | fromdate) - (.[0].last_updated | fromdate)) / 3600
  }
'

# Output:
{
  "previous": {"progress_pct": 1.31, "oldest_date": "2026-01-14", ...},
  "current": {"progress_pct": 1.44, "oldest_date": "2026-01-14", ...},
  "delta_pct": 0.13,
  "time_diff_hours": 4.5
}
```

### 2. Calcular Velocidade

```bash
tail -10 catalog/collect-progress.jsonl | jq -s '
  (.[0].last_updated | fromdate) as $first_time |
  (.[0].progress_pct) as $first_pct |
  (.[-1].last_updated | fromdate) as $last_time |
  (.[-1].progress_pct) as $last_pct |
  {
    time_span_hours: ($last_time - $first_time) / 3600,
    progress_delta: ($last_pct - $first_pct),
    velocity_pct_per_hour: (($last_pct - $first_pct) / (($last_time - $first_time) / 3600))
  }
'

# Output:
{
  "time_span_hours": 24,
  "progress_delta": 0.52,
  "velocity_pct_per_hour": 0.0217
}
```

### 3. Estimar ETA

```bash
tail -20 catalog/collect-progress.jsonl | jq -s '
  (.[0].last_updated | fromdate) as $first_time |
  (.[0].progress_pct) as $first_pct |
  (.[-1].last_updated | fromdate) as $last_time |
  (.[-1].progress_pct) as $last_pct |
  (($last_pct - $first_pct) / (($last_time - $first_time) / 3600)) as $velocity |
  (100 - $last_pct) as $remaining |
  ($remaining / $velocity) as $hours_remaining |
  {
    current_progress: $last_pct,
    remaining: $remaining,
    velocity_pct_per_hour: $velocity,
    eta_hours: $hours_remaining,
    eta_days: ($hours_remaining / 24)
  }
'

# Output:
{
  "current_progress": 1.44,
  "remaining": 98.56,
  "velocity_pct_per_hour": 0.0217,
  "eta_hours": 4542,
  "eta_days": 189.25
}
```

### 4. Detectar Quando Travou

```bash
# Encontra quando oldest_date parou de mudar
cat catalog/collect-progress.jsonl | jq -r '[.oldest_date, .last_updated] | @tsv' | \
  awk '{if ($1 == prev) count++; else count=0; prev=$1; if (count > 10) print "Stuck at " $1 " since " $2}'
```

### 5. Gráfico de Tendência (Python)

```python
import json
import matplotlib.pyplot as plt
from datetime import datetime

# Ler JSONL
with open('catalog/collect-progress.jsonl') as f:
    history = [json.loads(line) for line in f]

# Extrair dados
timestamps = [datetime.fromisoformat(h['last_updated'].replace('Z', '+00:00')) for h in history]
progress = [h['progress_pct'] for h in history]

# Plotar
plt.plot(timestamps, progress)
plt.xlabel('Time')
plt.ylabel('Progress %')
plt.title('Backfill Progress Over Time')
plt.grid(True)
plt.show()
```

## 🌐 Uso no Dashboard (JavaScript)

### Fetch e Parse

```javascript
// Fetch JSONL
const response = await fetch('https://archive.org/download/causaganha-catalog/collect-progress.jsonl')
const text = await response.text()

// Parse lines
const history = text.trim().split('\n').map(line => JSON.parse(line))

// Get current and previous
const current = history[history.length - 1]
const previous = history[history.length - 2]

// Calculate delta
const delta = {
  progress_pct: current.progress_pct - previous.progress_pct,
  time_hours: (new Date(current.last_updated) - new Date(previous.last_updated)) / 3600000
}

console.log(`Progress increased ${delta.progress_pct.toFixed(2)}% in ${delta.time_hours.toFixed(1)}h`)
// Output: "Progress increased 0.13% in 4.5h"
```

### Component React Exemplo

```jsx
import { useState, useEffect } from 'react'

function ProgressTrend() {
  const [trend, setTrend] = useState(null)

  useEffect(() => {
    fetch('/causaganha/collect-progress.jsonl')
      .then(res => res.text())
      .then(text => {
        const history = text.trim().split('\n').map(line => JSON.parse(line))
        const current = history[history.length - 1]
        const previous = history[history.length - 2]
        
        const timeDiff = (new Date(current.last_updated) - new Date(previous.last_updated)) / 3600000
        const progressDiff = current.progress_pct - previous.progress_pct
        const velocity = progressDiff / timeDiff
        const eta = (100 - current.progress_pct) / velocity
        
        setTrend({
          delta: progressDiff,
          velocity: velocity,
          eta_days: eta / 24
        })
      })
  }, [])

  if (!trend) return <div>Loading...</div>

  return (
    <div className="progress-trend">
      <h3>Progress Trend</h3>
      <p>Last change: +{trend.delta.toFixed(2)}%</p>
      <p>Velocity: {trend.velocity.toFixed(4)}% per hour</p>
      <p>ETA: ~{Math.round(trend.eta_days)} days</p>
    </div>
  )
}
```

## 📈 Análises Possíveis

### 1. Velocidade por Hora do Dia
Descobrir quando o pipeline roda mais rápido:

```bash
cat catalog/collect-progress.jsonl | jq -r '
  [.last_updated, .progress_pct] | @tsv
' | awk '{
  hour = substr($1, 12, 2)
  progress[hour] += $2
  count[hour]++
}
END {
  for (h in progress) print h, progress[h]/count[h]
}' | sort -n
```

### 2. Dias com Melhor Performance
```bash
cat catalog/collect-progress.jsonl | jq -r '
  [(.last_updated | split("T")[0]), .progress_pct] | @tsv
' | awk '{
  if (prev_date == $1) delta[$1] += $2 - prev_pct
  prev_date = $1
  prev_pct = $2
}
END {
  for (d in delta) print d, delta[d]
}' | sort -k2 -rn | head -10
```

### 3. Correlação oldest_date vs Progress
Ver se `oldest_date` avança correlaciona com `progress_pct`:

```bash
cat catalog/collect-progress.jsonl | jq -r '
  [.oldest_date, .progress_pct] | @tsv
' | awk '{
  if ($1 != prev_oldest && prev_oldest != "") print prev_oldest " -> " $1 ": " ($2 - prev_pct) "%"
  prev_oldest = $1
  prev_pct = $2
}'
```

## 🔄 Rotação de Logs

JSONL cresce infinitamente. Considere rotação:

```bash
# Manter últimos 1000 entries
tail -1000 collect-progress.jsonl > collect-progress.jsonl.tmp
mv collect-progress.jsonl.tmp collect-progress.jsonl
```

Ou comprimir histórico antigo:

```bash
# Comprimir entries mais antigas que 30 dias
cat collect-progress.jsonl | \
  jq -r 'select((.last_updated | fromdate) > (now - 30*24*3600)) | tojson' \
  > collect-progress.recent.jsonl

cat collect-progress.jsonl | \
  jq -r 'select((.last_updated | fromdate) <= (now - 30*24*3600)) | tojson' \
  | gzip > collect-progress.archive.jsonl.gz
```

## 🎯 Best Practices

1. **Sempre append, nunca truncate** - JSONL é append-only
2. **Uma linha = um timestamp** - Facilita comparações temporais
3. **Parse defensivo** - Linhas podem ser malformadas, use try/catch
4. **Cache resultados** - Parsear 1000+ linhas pode ser lento
5. **Compressão** - JSONL comprime muito bem (gzip)

---

**Criado:** 2026-02-05  
**Formato:** JSONL (JSON Lines)  
**Compatibilidade:** Backward compatible com .json
