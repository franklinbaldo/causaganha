/**
 * DJEN Scraper - Cloudflare Worker
 *
 * Coleta comunicações do DJEN via bulk download (caderno)
 * Armazena ZIPs no R2 e estado no KV
 *
 * Estratégia: Download de cadernos completos
 * - Usa endpoint /api/v1/caderno/{tribunal}/{date}/D
 * - Baixa ZIP completo de cada tribunal (sem limite de 10k)
 * - Processa 1 tribunal por execução
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

interface State {
	d1: {
		date: string;
		status: 'in_progress' | 'complete';
		tribunais_done: string[];
		tribunais_pending: string[];
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

			// Determinar próximo tribunal
			const tribunal = getNextTribunal(state);

			if (!tribunal) {
				console.log('✅ Todos os tribunais processados para', state.d1.date);
				return;
			}

			console.log(`📅 Date: ${state.d1.date} | 🏛️ Tribunal: ${tribunal}`);

			// Buscar info do caderno
			const cadernoInfo = await fetchCadernoInfo(env, state.d1.date, tribunal);

			if (!cadernoInfo) {
				console.log(`⚠️ Caderno não disponível para ${tribunal}`);
				await markTribunalDone(env, state, tribunal, 0);
				return;
			}

			console.log(`📦 Caderno: ${cadernoInfo.total_comunicacoes} comunicações, ${(cadernoInfo.tamanho_bytes / 1024 / 1024).toFixed(1)}MB`);

			// Baixar e salvar ZIP no R2
			await downloadAndSaveZip(env, state.d1.date, tribunal, cadernoInfo);

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
			tribunais_done: [],
			tribunais_pending: [...TRIBUNAIS],
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

function getNextTribunal(state: State): string | null {
	const yesterday = getDateString(-1);

	// Se D-1 mudou, resetar
	if (state.d1.date !== yesterday) {
		state.d1 = {
			date: yesterday,
			status: 'in_progress',
			tribunais_done: [],
			tribunais_pending: [...TRIBUNAIS],
			records: 0
		};
	}

	// Se já completou
	if (state.d1.status === 'complete') {
		return null;
	}

	// Pegar próximo tribunal pendente
	if (state.d1.tribunais_pending.length > 0) {
		return state.d1.tribunais_pending[0];
	}

	// Todos processados
	state.d1.status = 'complete';
	return null;
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
	state.d1.tribunais_done.push(tribunal);
	state.d1.tribunais_pending = state.d1.tribunais_pending.filter(t => t !== tribunal);
	state.d1.records += recordCount;
	state.stats.total_records += recordCount;
	state.stats.last_run = new Date().toISOString();

	console.log(`🎉 ${tribunal} completo! Restam ${state.d1.tribunais_pending.length} tribunais`);

	// Se não tem mais tribunais, dia completo
	if (state.d1.tribunais_pending.length === 0) {
		state.d1.status = 'complete';
		state.backfill.completed_dates.push(state.d1.date);
		state.stats.total_days_archived += 1;
		console.log(`🏆 Dia ${state.d1.date} completo! Total: ${state.d1.records} comunicações`);
	}

	await env.DJEN_STATE.put('state', JSON.stringify(state));
}

function getDateString(daysOffset: number): string {
	const date = new Date();
	date.setDate(date.getDate() + daysOffset);
	return date.toISOString().split('T')[0];
}
