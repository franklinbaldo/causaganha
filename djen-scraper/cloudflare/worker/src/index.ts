/**
 * DJEN Scraper - Cloudflare Worker
 *
 * Coleta comunicações do DJEN via proxy brasileiro (Cloud Run)
 * Armazena dados no R2 e estado no KV
 *
 * Estratégia: Paginação inteligente
 * - Processa 1 órgão por vez, várias páginas
 * - Continua de onde parou (last_page)
 * - Quando terminar um órgão, passa para o próximo
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
		current_orgao: string | null;
		current_page: number;
		orgaos_done: string[];
		orgaos_pending: string[];
		records: number;
	};
	backfill: {
		next_date: string | null;
		oldest_target: string;
		completed_dates: string[];
	};
	stats: {
		total_records: number;
		total_days_archived: number;
		last_run: string;
		errors_today: number;
	};
}

// Lista de órgãos DJEN
const ORGAOS = [
	'TRF1', 'TRF2', 'TRF3', 'TRF4', 'TRF5', 'TRF6',
	'TST', 'TSE', 'STM', 'STJ', 'STF',
	'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDF', 'TJES',
	'TJGO', 'TJMA', 'TJMG', 'TJMS', 'TJMT', 'TJPA', 'TJPB', 'TJPE',
	'TJPI', 'TJPR', 'TJRJ', 'TJRN', 'TJRO', 'TJRR', 'TJRS', 'TJSC',
	'TJSE', 'TJSP', 'TJTO'
];

// Quantas páginas buscar por execução (respeitando limite de 50 subrequests)
const PAGES_PER_BATCH = 10;
const ITEMS_PER_PAGE = 100;

export default {
	async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
		console.log('🚀 DJEN Scraper - Iniciando batch', new Date().toISOString());

		try {
			const state = await loadState(env);

			// Determinar órgão e página atual
			const { orgao, startPage } = getCurrentTarget(state);

			if (!orgao) {
				console.log('✅ Todos os órgãos processados para', state.d1.date);
				return;
			}

			console.log(`📅 Date: ${state.d1.date} | 📁 Órgão: ${orgao} | 📄 Página: ${startPage}`);

			// Buscar várias páginas do mesmo órgão
			const { items, lastPage, hasMore } = await fetchPages(env, state.d1.date, orgao, startPage);

			// Salvar dados no R2
			if (items.length > 0) {
				await saveToR2(env, state.d1.date, orgao, startPage, items);
			}

			// Atualizar estado
			await updateState(env, state, orgao, items.length, lastPage, hasMore);

			console.log(`✅ Coletados ${items.length} items | Página ${startPage}-${lastPage} | Mais: ${hasMore}`);

		} catch (error) {
			console.error('❌ Erro no batch:', error);
			throw error;
		}
	},

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
			const event = {} as ScheduledEvent;
			await this.scheduled(event, env, { waitUntil: () => {} } as ExecutionContext);
			return Response.json({ status: 'triggered' });
		}

		if (url.pathname === '/reset' && request.method === 'POST') {
			await env.DJEN_STATE.delete('state');
			return Response.json({ status: 'reset' });
		}

		return Response.json({ error: 'Not found' }, { status: 404 });
	}
};

async function loadState(env: Env): Promise<State> {
	const stored = await env.DJEN_STATE.get('state', 'json');

	if (stored) {
		return stored as State;
	}

	const yesterday = getDateString(-1);
	return {
		d1: {
			date: yesterday,
			status: 'in_progress',
			current_orgao: null,
			current_page: 1,
			orgaos_done: [],
			orgaos_pending: [...ORGAOS],
			records: 0
		},
		backfill: {
			next_date: null,
			oldest_target: '2020-01-01',
			completed_dates: []
		},
		stats: {
			total_records: 0,
			total_days_archived: 0,
			last_run: new Date().toISOString(),
			errors_today: 0
		}
	};
}

function getCurrentTarget(state: State): { orgao: string | null; startPage: number } {
	const yesterday = getDateString(-1);

	// Se D-1 mudou, resetar
	if (state.d1.date !== yesterday) {
		state.d1 = {
			date: yesterday,
			status: 'in_progress',
			current_orgao: null,
			current_page: 1,
			orgaos_done: [],
			orgaos_pending: [...ORGAOS],
			records: 0
		};
	}

	// Se já completou
	if (state.d1.status === 'complete') {
		return { orgao: null, startPage: 1 };
	}

	// Se tem órgão em andamento
	if (state.d1.current_orgao) {
		return { orgao: state.d1.current_orgao, startPage: state.d1.current_page };
	}

	// Pegar próximo órgão pendente
	if (state.d1.orgaos_pending.length > 0) {
		return { orgao: state.d1.orgaos_pending[0], startPage: 1 };
	}

	// Todos processados
	state.d1.status = 'complete';
	return { orgao: null, startPage: 1 };
}

async function fetchPages(
	env: Env,
	date: string,
	orgao: string,
	startPage: number
): Promise<{ items: any[]; lastPage: number; hasMore: boolean }> {
	const proxyUrl = env.PROXY_URL || 'https://djen-proxy-mhgmawcn3a-rj.a.run.app';
	const allItems: any[] = [];
	let currentPage = startPage;
	let hasMore = true;

	for (let i = 0; i < PAGES_PER_BATCH && hasMore; i++) {
		try {
			const url = `${proxyUrl}/api/v1/comunicacao?dataPublicacao=${date}&idOrgao=${orgao}&pagina=${currentPage}&itensPorPagina=${ITEMS_PER_PAGE}`;

			console.log(`📥 Fetching ${orgao} página ${currentPage}...`);

			const response = await fetch(url, {
				method: 'GET',
				headers: { 'Accept': 'application/json' }
			});

			if (!response.ok) {
				await response.text();
				console.error(`❌ Erro ${orgao} p${currentPage}: ${response.status}`);

				if (response.status === 429) {
					console.log('⏸️ Rate limited, parando batch');
					break;
				}
				// 5xx (incluindo 500 para páginas além do range) = fim dos dados
				if (response.status >= 500) {
					console.log(`🏁 ${orgao} p${currentPage}: 5xx indica fim dos dados`);
					hasMore = false;
					break;
				}
				// 4xx: pular para próxima página
				currentPage++;
				continue;
			}

			const data = await response.json();
			const items = data.items || [];

			console.log(`✅ ${orgao} p${currentPage}: ${items.length} items (total API: ${data.count || 0})`);

			allItems.push(...items);

			// Se retornou menos que o máximo, acabaram as páginas
			if (items.length < ITEMS_PER_PAGE) {
				hasMore = false;
			} else {
				currentPage++;
			}

			// Pequeno delay para não sobrecarregar
			await new Promise(resolve => setTimeout(resolve, 100));

		} catch (error) {
			console.error(`❌ Erro ${orgao} p${currentPage}:`, error);
			break;
		}
	}

	return { items: allItems, lastPage: currentPage, hasMore };
}

async function saveToR2(env: Env, date: string, orgao: string, startPage: number, items: any[]): Promise<void> {
	const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
	const key = `data/${date}/${orgao}_p${startPage}_${timestamp}.json`;

	const json = JSON.stringify({ orgao, date, startPage, count: items.length, items }, null, 0);

	await env.DJEN_STORAGE.put(key, json, {
		httpMetadata: { contentType: 'application/json' }
	});

	console.log(`💾 Salvou ${key} (${json.length} bytes, ${items.length} items)`);
}

async function updateState(
	env: Env,
	state: State,
	orgao: string,
	itemCount: number,
	lastPage: number,
	hasMore: boolean
): Promise<void> {
	state.d1.records += itemCount;
	state.stats.total_records += itemCount;
	state.stats.last_run = new Date().toISOString();

	if (hasMore) {
		// Continuar no mesmo órgão, próxima página
		// lastPage já é o próximo a buscar (currentPage++ ocorre após cada fetch)
		state.d1.current_orgao = orgao;
		state.d1.current_page = lastPage;
	} else {
		// Órgão completo, passar para o próximo
		state.d1.orgaos_done.push(orgao);
		state.d1.orgaos_pending = state.d1.orgaos_pending.filter(o => o !== orgao);
		state.d1.current_orgao = null;
		state.d1.current_page = 1;

		console.log(`🎉 ${orgao} completo! Restam ${state.d1.orgaos_pending.length} órgãos`);

		// Se não tem mais órgãos, dia completo
		if (state.d1.orgaos_pending.length === 0) {
			state.d1.status = 'complete';
			state.backfill.completed_dates.push(state.d1.date);
			state.stats.total_days_archived += 1;
			console.log(`🏆 Dia ${state.d1.date} completo!`);
		}
	}

	await env.DJEN_STATE.put('state', JSON.stringify(state));
}

function getDateString(daysOffset: number): string {
	const date = new Date();
	date.setDate(date.getDate() + daysOffset);
	return date.toISOString().split('T')[0];
}
