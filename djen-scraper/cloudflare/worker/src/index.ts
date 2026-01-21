/**
 * DJEN Scraper - Cloudflare Worker
 *
 * Coleta comunicações do DJEN via proxy brasileiro (Cloud Run)
 * Armazena dados comprimidos no R2 e estado no KV
 *
 * Executa a cada minuto via Cron (50 requests/batch)
 */

interface Env {
	DJEN_STATE: KVNamespace;
	DJEN_STORAGE: R2Bucket;
	PROXY_URL: string;
}

interface State {
	d1: {
		date: string;
		status: 'in_progress' | 'complete';
		orgaos_done: string[];
		orgaos_pending: string[];
		records: number;
		last_page: Record<string, number>;
	};
	backfill: {
		next_date: string | null;
		oldest_target: string;
		completed_dates: string[];
		status: 'idle' | 'in_progress';
	};
	stats: {
		total_records: number;
		total_days_archived: number;
		last_run: string;
		errors_today: number;
	};
}

// Lista de órgãos DJEN (27 tribunais)
const ORGAOS = [
	'TRF1', 'TRF2', 'TRF3', 'TRF4', 'TRF5', 'TRF6',
	'TST', 'TSE', 'STM', 'STJ', 'STF',
	'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDF', 'TJES',
	'TJGO', 'TJMA', 'TJMG', 'TJMS', 'TJMT', 'TJPA', 'TJPB', 'TJPE',
	'TJPI', 'TJPR', 'TJRJ', 'TJRN', 'TJRO', 'TJRR', 'TJRS', 'TJSC',
	'TJSE', 'TJSP', 'TJTO'
];

const BATCH_SIZE = 5; // Reduzido para evitar rate limiting (429)

export default {
	async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
		console.log('🚀 DJEN Scraper - Iniciando batch', new Date().toISOString());

		try {
			// 1. Carregar estado
			const state = await loadState(env);

			// 2. Determinar prioridade
			const { targetDate, orgaos } = await determinePriority(state);

			console.log(`📅 Target date: ${targetDate}`);
			console.log(`📊 Órgãos pendentes: ${orgaos.length}`);

			// 3. Executar batch de requests
			const results = await executeBatch(env, targetDate, orgaos);

			// 4. Salvar dados no R2
			if (results.length > 0) {
				await saveToR2(env, targetDate, results);
			}

			// 5. Atualizar estado
			await updateState(env, state, targetDate, results);

			console.log(`✅ Batch completo: ${results.length} registros coletados`);

		} catch (error) {
			console.error('❌ Erro no batch:', error);
			throw error;
		}
	},

	// Endpoint HTTP para debug/teste manual
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);

		if (url.pathname === '/health') {
			return Response.json({ status: 'ok', timestamp: new Date().toISOString() });
		}

		if (url.pathname === '/state') {
			const state = await loadState(env);
			return Response.json(state);
		}

		if (url.pathname === '/trigger' && request.method === 'POST') {
			// Trigger manual (útil para testes)
			const event = {} as ScheduledEvent;
			await this.scheduled(event, env, { waitUntil: () => {} } as ExecutionContext);
			return Response.json({ status: 'triggered' });
		}

		return Response.json({ error: 'Not found' }, { status: 404 });
	}
};

/**
 * Carrega estado do KV (ou cria inicial)
 */
async function loadState(env: Env): Promise<State> {
	const stored = await env.DJEN_STATE.get('state', 'json');

	if (stored) {
		return stored as State;
	}

	// Estado inicial
	const yesterday = getDateString(-1);
	return {
		d1: {
			date: yesterday,
			status: 'in_progress',
			orgaos_done: [],
			orgaos_pending: [...ORGAOS],
			records: 0,
			last_page: {}
		},
		backfill: {
			next_date: null,
			oldest_target: '2020-01-01',
			completed_dates: [],
			status: 'idle'
		},
		stats: {
			total_records: 0,
			total_days_archived: 0,
			last_run: new Date().toISOString(),
			errors_today: 0
		}
	};
}

/**
 * Determina qual data/órgãos processar (prioridade D-1)
 */
async function determinePriority(state: State): Promise<{ targetDate: string; orgaos: string[] }> {
	const yesterday = getDateString(-1);

	// Se D-1 mudou, resetar estado
	if (state.d1.date !== yesterday) {
		state.d1 = {
			date: yesterday,
			status: 'in_progress',
			orgaos_done: [],
			orgaos_pending: [...ORGAOS],
			records: 0,
			last_page: {}
		};
	}

	// Prioridade 1: D-1 incompleto
	if (state.d1.status === 'in_progress' && state.d1.orgaos_pending.length > 0) {
		return {
			targetDate: state.d1.date,
			orgaos: state.d1.orgaos_pending.slice(0, BATCH_SIZE)
		};
	}

	// D-1 completo, marcar como tal
	if (state.d1.status === 'in_progress') {
		state.d1.status = 'complete';
	}

	// Prioridade 2: Backfill
	if (!state.backfill.next_date) {
		// Inicializar backfill com data anterior a D-1
		state.backfill.next_date = getDateString(-2);
	}

	return {
		targetDate: state.backfill.next_date,
		orgaos: ORGAOS.slice(0, BATCH_SIZE)
	};
}

/**
 * Executa batch de requests ao DJEN via proxy (sequencial para evitar 429)
 */
async function executeBatch(env: Env, date: string, orgaos: string[]): Promise<any[]> {
	const proxyUrl = env.PROXY_URL || 'https://djen-proxy-mhgmawcn3a-rj.a.run.app';
	const results: any[] = [];

	// Fazer requests SEQUENCIAIS para evitar rate limiting
	for (const orgao of orgaos) {
		try {
			const url = `${proxyUrl}/api/v1/comunicacao?dataPublicacao=${date}&idOrgao=${orgao}`;

			const response = await fetch(url, {
				method: 'GET',
				headers: {
					'Accept': 'application/json'
				}
			});

			if (!response.ok) {
				// Consumir body para evitar stalled response warning
				await response.text();
				console.error(`❌ Erro ${orgao}: ${response.status}`);

				// Se rate limited, parar o batch
				if (response.status === 429) {
					console.log('⏸️ Rate limited, parando batch');
					break;
				}
				continue;
			}

			const data = await response.json();

			// API retorna { status, message, count, items }
			const items = data.items || [];
			const count = data.count || 0;

			results.push({
				orgao,
				date,
				count,
				items,
				timestamp: new Date().toISOString()
			});

			console.log(`✅ ${orgao}: ${items.length} items (total: ${count})`);

			// Pequeno delay entre requests (200ms)
			await new Promise(resolve => setTimeout(resolve, 200));

		} catch (error) {
			console.error(`❌ Erro ${orgao}:`, error);
		}
	}

	return results;
}

/**
 * Salva dados no R2 (JSON)
 */
async function saveToR2(env: Env, date: string, results: any[]): Promise<void> {
	const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
	const key = `data/${date}/${timestamp}.json`;

	const json = JSON.stringify(results, null, 0);

	await env.DJEN_STORAGE.put(key, json, {
		httpMetadata: {
			contentType: 'application/json'
		}
	});

	console.log(`💾 Salvou ${key} (${json.length} bytes)`);
}

/**
 * Atualiza estado no KV
 */
async function updateState(env: Env, state: State, targetDate: string, results: any[]): Promise<void> {
	// Contar items coletados (data.items) não o count total da API
	const recordCount = results.reduce((sum, r) => sum + (r.items?.length || 0), 0);

	// Atualizar D-1
	if (targetDate === state.d1.date) {
		const orgaosDone = results.map(r => r.orgao);
		state.d1.orgaos_done.push(...orgaosDone);
		state.d1.orgaos_pending = state.d1.orgaos_pending.filter(o => !orgaosDone.includes(o));
		state.d1.records += recordCount;

		if (state.d1.orgaos_pending.length === 0) {
			state.d1.status = 'complete';
			state.backfill.completed_dates.push(targetDate);
			state.stats.total_days_archived += 1;
		}
	} else {
		// Backfill
		// Simplificado: assumir que batch pequeno completa a data
		state.backfill.completed_dates.push(targetDate);
		state.backfill.next_date = getPreviousDate(targetDate);
		state.stats.total_days_archived += 1;
	}

	state.stats.total_records += recordCount;
	state.stats.last_run = new Date().toISOString();

	await env.DJEN_STATE.put('state', JSON.stringify(state));
	console.log('📝 Estado atualizado');
}

/**
 * Helpers
 */
function getDateString(daysOffset: number): string {
	const date = new Date();
	date.setDate(date.getDate() + daysOffset);
	return date.toISOString().split('T')[0];
}

function getPreviousDate(dateStr: string): string {
	const date = new Date(dateStr);
	date.setDate(date.getDate() - 1);
	return date.toISOString().split('T')[0];
}
