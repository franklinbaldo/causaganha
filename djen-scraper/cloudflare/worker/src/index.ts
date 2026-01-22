/**
 * DJEN Scraper - Cloudflare Worker
 *
 * Coleta comunicações do DJEN via bulk download (caderno)
 * Armazena ZIPs no R2 e estado no KV
 *
 * Estratégia:
 * 1. Prioridade: D-1 (ontem) - sempre processa primeiro
 * 2. Backfill: Após D-1 completo, volta no tempo até oldest_target
 * 3. Download de cadernos completos (sem limite de 10k)
 */

interface Env {
	DJEN_STATE: KVNamespace;
	DJEN_STORAGE: R2Bucket;
	PROXY_URL: string;
}

interface CadernoInfo {
	tribunal: string;
	sigla_tribunal: string;
	meio: string;
	status: string;
	versao: number;
	data: string;
	total_comunicacoes: number;
	numero_paginas: number;
	tamanho_bytes: number;
	hash: string;
	url: string;
}

interface DayJob {
	date: string;
	status: 'in_progress' | 'complete';
	tribunais_done: string[];
	tribunais_pending: string[];
	records: number;
}

interface State {
	// Job atual (D-1 ou backfill)
	current: DayJob;
	// Modo: 'd1' = processando D-1, 'backfill' = processando histórico
	mode: 'd1' | 'backfill';
	// Backfill tracking
	backfill: {
		oldest_target: string;
		completed_dates: string[];
		skipped_dates: string[]; // datas sem dados
	};
	// Stats globais
	stats: {
		total_records: number;
		total_days_archived: number;
		last_run: string;
		errors_today: number;
	};
}

// Lista completa de tribunais DJEN (92)
const TRIBUNAIS = [
	// Tribunais Regionais Federais (6)
	'TRF1', 'TRF2', 'TRF3', 'TRF4', 'TRF5', 'TRF6',
	// Tribunais Superiores (5)
	'TST', 'TSE', 'STM', 'STJ', 'STF',
	// Conselhos e outros (3)
	'CNJ', 'CNMP', 'TNU',
	// Tribunais de Justiça Estaduais (27)
	'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDF', 'TJES',
	'TJGO', 'TJMA', 'TJMG', 'TJMS', 'TJMT', 'TJPA', 'TJPB', 'TJPE',
	'TJPI', 'TJPR', 'TJRJ', 'TJRN', 'TJRO', 'TJRR', 'TJRS', 'TJSC',
	'TJSE', 'TJSP', 'TJTO',
	// Tribunais Regionais do Trabalho (24)
	'TRT1', 'TRT2', 'TRT3', 'TRT4', 'TRT5', 'TRT6', 'TRT7', 'TRT8',
	'TRT9', 'TRT10', 'TRT11', 'TRT12', 'TRT13', 'TRT14', 'TRT15', 'TRT16',
	'TRT17', 'TRT18', 'TRT19', 'TRT20', 'TRT21', 'TRT22', 'TRT23', 'TRT24',
	// Tribunais Regionais Eleitorais (27)
	'TREAC', 'TREAL', 'TREAM', 'TREAP', 'TREBA', 'TRECE', 'TREDF', 'TREES',
	'TREGO', 'TREMA', 'TREMG', 'TREMS', 'TREMT', 'TREPA', 'TREPB', 'TREPE',
	'TREPI', 'TREPR', 'TRERJ', 'TRERN', 'TRERO', 'TRERR', 'TRERS', 'TRESC',
	'TRESE', 'TRESP', 'TRETO'
];

export default {
	async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
		console.log('🚀 DJEN Scraper - Iniciando', new Date().toISOString());

		try {
			const state = await loadState(env);

			// Verificar se D-1 mudou (novo dia)
			const yesterday = getDateString(-1);
			if (state.mode === 'd1' && state.current.date !== yesterday) {
				// Novo dia! Resetar para D-1
				console.log(`📅 Novo dia detectado! Mudando de ${state.current.date} para ${yesterday}`);
				state.current = createDayJob(yesterday);
				state.mode = 'd1';
			}

			// Determinar próximo trabalho
			const { date, tribunal } = getNextWork(state);

			if (!tribunal) {
				console.log('✅ Nenhum trabalho pendente');
				await env.DJEN_STATE.put('state', JSON.stringify(state));
				return;
			}

			const modeLabel = state.mode === 'd1' ? '🔴 D-1' : '🔵 Backfill';
			console.log(`${modeLabel} | 📅 ${date} | 🏛️ ${tribunal}`);

			// Buscar info do caderno
			const cadernoInfo = await fetchCadernoInfo(env, date, tribunal);

			if (!cadernoInfo) {
				console.log(`⚠️ Caderno não disponível para ${tribunal}`);
				await markTribunalDone(env, state, tribunal, 0);
				return;
			}

			console.log(`📦 Caderno: ${cadernoInfo.total_comunicacoes} comunicações, ${(cadernoInfo.tamanho_bytes / 1024 / 1024).toFixed(1)}MB`);

			// Baixar e salvar ZIP no R2
			await downloadAndSaveZip(env, date, tribunal, cadernoInfo);

			// Marcar tribunal como completo
			await markTribunalDone(env, state, tribunal, cadernoInfo.total_comunicacoes);

			console.log(`✅ ${tribunal} completo! ${cadernoInfo.total_comunicacoes} comunicações`);

		} catch (error) {
			console.error('❌ Erro:', error);
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

function createDayJob(date: string): DayJob {
	return {
		date,
		status: 'in_progress',
		tribunais_done: [],
		tribunais_pending: [...TRIBUNAIS],
		records: 0
	};
}

async function loadState(env: Env): Promise<State> {
	const stored = await env.DJEN_STATE.get('state', 'json');

	if (stored) {
		// Migrar estado antigo se necessário
		const state = stored as any;
		if (state.d1 && !state.current) {
			// Migrar do formato antigo
			return {
				current: {
					date: state.d1.date,
					status: state.d1.status,
					tribunais_done: state.d1.tribunais_done || [],
					tribunais_pending: state.d1.tribunais_pending || [],
					records: state.d1.records || 0
				},
				mode: 'd1',
				backfill: {
					oldest_target: state.backfill?.oldest_target || '2020-01-01',
					completed_dates: state.backfill?.completed_dates || [],
					skipped_dates: []
				},
				stats: state.stats || {
					total_records: 0,
					total_days_archived: 0,
					last_run: new Date().toISOString(),
					errors_today: 0
				}
			};
		}
		return state as State;
	}

	const yesterday = getDateString(-1);
	return {
		current: createDayJob(yesterday),
		mode: 'd1',
		backfill: {
			oldest_target: '2020-01-01',
			completed_dates: [],
			skipped_dates: []
		},
		stats: {
			total_records: 0,
			total_days_archived: 0,
			last_run: new Date().toISOString(),
			errors_today: 0
		}
	};
}

function getNextWork(state: State): { date: string; tribunal: string | null } {
	// Se job atual tem tribunais pendentes, continuar
	if (state.current.tribunais_pending.length > 0) {
		return {
			date: state.current.date,
			tribunal: state.current.tribunais_pending[0]
		};
	}

	// Job atual completo
	if (state.current.status !== 'complete') {
		state.current.status = 'complete';
	}

	// Se estava em D-1, iniciar backfill
	if (state.mode === 'd1') {
		// Adicionar D-1 às datas completas
		if (!state.backfill.completed_dates.includes(state.current.date)) {
			state.backfill.completed_dates.push(state.current.date);
			state.stats.total_days_archived += 1;
		}

		// Encontrar próxima data para backfill (D-2, D-3, etc.)
		const nextBackfillDate = findNextBackfillDate(state);

		if (nextBackfillDate) {
			console.log(`🔄 D-1 completo! Iniciando backfill: ${nextBackfillDate}`);
			state.mode = 'backfill';
			state.current = createDayJob(nextBackfillDate);
			return {
				date: nextBackfillDate,
				tribunal: state.current.tribunais_pending[0]
			};
		} else {
			console.log('🏆 Backfill completo até', state.backfill.oldest_target);
			return { date: state.current.date, tribunal: null };
		}
	}

	// Estava em backfill, encontrar próxima data
	if (!state.backfill.completed_dates.includes(state.current.date)) {
		state.backfill.completed_dates.push(state.current.date);
		state.stats.total_days_archived += 1;
	}

	const nextBackfillDate = findNextBackfillDate(state);

	if (nextBackfillDate) {
		console.log(`🔄 Backfill: próxima data ${nextBackfillDate}`);
		state.current = createDayJob(nextBackfillDate);
		return {
			date: nextBackfillDate,
			tribunal: state.current.tribunais_pending[0]
		};
	}

	console.log('🏆 Backfill completo!');
	return { date: state.current.date, tribunal: null };
}

function findNextBackfillDate(state: State): string | null {
	const yesterday = getDateString(-1);
	const oldestTarget = new Date(state.backfill.oldest_target);
	const allCompleted = new Set([
		...state.backfill.completed_dates,
		...state.backfill.skipped_dates
	]);

	// Começar de D-2 e ir para trás
	let checkDate = new Date(yesterday);
	checkDate.setDate(checkDate.getDate() - 1); // D-2

	while (checkDate >= oldestTarget) {
		const dateStr = checkDate.toISOString().split('T')[0];

		if (!allCompleted.has(dateStr)) {
			return dateStr;
		}

		checkDate.setDate(checkDate.getDate() - 1);
	}

	return null; // Backfill completo
}

async function fetchCadernoInfo(env: Env, date: string, tribunal: string): Promise<CadernoInfo | null> {
	const proxyUrl = env.PROXY_URL || 'https://djen-proxy-mhgmawcn3a-rj.a.run.app';
	const url = `${proxyUrl}/api/v1/caderno/${tribunal}/${date}/D`;

	console.log(`📥 Buscando caderno: ${url}`);

	try {
		const response = await fetch(url, {
			method: 'GET',
			headers: { 'Accept': 'application/json' }
		});

		if (!response.ok) {
			const text = await response.text();
			console.error(`❌ Erro ao buscar caderno: ${response.status} - ${text}`);
			return null;
		}

		const data = await response.json() as CadernoInfo;

		// Verificar se o caderno está processado
		if (data.status !== 'Processado') {
			console.log(`⏳ Caderno ${tribunal} status: ${data.status}`);
			return null;
		}

		return data;
	} catch (error) {
		console.error(`❌ Erro ao buscar caderno ${tribunal}:`, error);
		return null;
	}
}

async function downloadAndSaveZip(env: Env, date: string, tribunal: string, info: CadernoInfo): Promise<void> {
	console.log(`📥 Baixando ZIP de ${tribunal}...`);

	// Baixar o ZIP da URL temporária
	const response = await fetch(info.url);

	if (!response.ok) {
		throw new Error(`Erro ao baixar ZIP: ${response.status}`);
	}

	// Salvar no R2
	const key = `cadernos/${date}/${tribunal}-D-${date}_v${info.versao}.zip`;

	await env.DJEN_STORAGE.put(key, response.body, {
		httpMetadata: { contentType: 'application/zip' },
		customMetadata: {
			tribunal: info.sigla_tribunal,
			date: date,
			total_comunicacoes: String(info.total_comunicacoes),
			hash: info.hash,
			versao: String(info.versao)
		}
	});

	console.log(`💾 Salvou ${key} (${(info.tamanho_bytes / 1024 / 1024).toFixed(1)}MB, ${info.total_comunicacoes} comunicações)`);
}

async function markTribunalDone(env: Env, state: State, tribunal: string, recordCount: number): Promise<void> {
	state.current.tribunais_done.push(tribunal);
	state.current.tribunais_pending = state.current.tribunais_pending.filter(t => t !== tribunal);
	state.current.records += recordCount;
	state.stats.total_records += recordCount;
	state.stats.last_run = new Date().toISOString();

	const remaining = state.current.tribunais_pending.length;
	console.log(`🎉 ${tribunal} completo! Restam ${remaining} tribunais para ${state.current.date}`);

	// Se não tem mais tribunais, dia completo
	if (remaining === 0) {
		state.current.status = 'complete';
		console.log(`🏆 Dia ${state.current.date} completo! Total: ${state.current.records} comunicações`);
	}

	await env.DJEN_STATE.put('state', JSON.stringify(state));
}

function getDateString(daysOffset: number): string {
	const date = new Date();
	date.setDate(date.getDate() + daysOffset);
	return date.toISOString().split('T')[0];
}
