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
		const corsHeaders = {
			'Access-Control-Allow-Origin': '*',
			'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
			'Access-Control-Allow-Headers': 'Content-Type'
		};

		if (request.method === 'OPTIONS') {
			return new Response(null, { headers: corsHeaders });
		}

		if (url.pathname === '/health') {
			return Response.json({ status: 'ok', timestamp: new Date().toISOString() }, { headers: corsHeaders });
		}

		if (url.pathname === '/state') {
			const state = await loadState(env);
			return Response.json(state, { headers: corsHeaders });
		}

		if (url.pathname === '/api/tribunais') {
			const data = await listTribunaisData(env);
			return Response.json(data, { headers: corsHeaders });
		}

		if (url.pathname.startsWith('/api/tribunal/')) {
			const tribunal = url.pathname.split('/')[3]?.toUpperCase();
			if (tribunal && TRIBUNAIS.includes(tribunal)) {
				const data = await getTribunalDetails(env, tribunal);
				return Response.json(data, { headers: corsHeaders });
			}
			return Response.json({ error: 'Tribunal not found' }, { status: 404, headers: corsHeaders });
		}

		if (url.pathname === '/' || url.pathname === '/dashboard') {
			const state = await loadState(env);
			return new Response(renderDashboard(state), {
				headers: { 'Content-Type': 'text/html; charset=utf-8' }
			});
		}

		if (url.pathname === '/trigger' && request.method === 'POST') {
			const event = {} as ScheduledEvent;
			await this.scheduled(event, env, { waitUntil: () => {} } as ExecutionContext);
			return Response.json({ status: 'triggered' }, { headers: corsHeaders });
		}

		if (url.pathname === '/reset' && request.method === 'POST') {
			await env.DJEN_STATE.delete('state');
			return Response.json({ status: 'reset' }, { headers: corsHeaders });
		}

		return Response.json({ error: 'Not found' }, { status: 404, headers: corsHeaders });
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

function renderDashboard(state: State): string {
	const progress = state.current.tribunais_done.length;
	const total = progress + state.current.tribunais_pending.length;
	const pct = total > 0 ? Math.round((progress / total) * 100) : 0;
	const modeEmoji = state.mode === 'd1' ? '🔴' : '🔵';
	const modeLabel = state.mode === 'd1' ? 'D-1 (Ontem)' : 'Backfill';

	return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<meta http-equiv="refresh" content="30">
	<title>DJEN Scraper Dashboard</title>
	<style>
		* { box-sizing: border-box; margin: 0; padding: 0; }
		body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; }
		.container { max-width: 1200px; margin: 0 auto; }
		h1 { font-size: 2rem; margin-bottom: 20px; }
		.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
		.card { background: #1e293b; border-radius: 12px; padding: 20px; }
		.card h2 { font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; }
		.card .value { font-size: 2rem; font-weight: bold; }
		.card .sub { font-size: 0.85rem; color: #64748b; margin-top: 5px; }
		.progress-bar { background: #334155; border-radius: 8px; height: 24px; overflow: hidden; margin: 10px 0; }
		.progress-fill { background: linear-gradient(90deg, #3b82f6, #8b5cf6); height: 100%; transition: width 0.3s; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: bold; }
		.tribunais { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 8px; margin-top: 15px; }
		.tribunal { padding: 6px 8px; border-radius: 6px; font-size: 0.75rem; text-align: center; }
		.done { background: #166534; color: #bbf7d0; }
		.pending { background: #334155; color: #94a3b8; }
		.mode-d1 { border-left: 4px solid #ef4444; }
		.mode-backfill { border-left: 4px solid #3b82f6; }
		.stats { display: flex; gap: 30px; flex-wrap: wrap; }
		.stat { text-align: center; }
		.stat .num { font-size: 1.5rem; font-weight: bold; color: #22c55e; }
		.stat .label { font-size: 0.8rem; color: #64748b; }
		footer { margin-top: 30px; text-align: center; color: #64748b; font-size: 0.8rem; }
	</style>
</head>
<body>
	<div class="container">
		<h1>📊 DJEN Scraper Dashboard</h1>

		<div class="cards">
			<div class="card ${state.mode === 'd1' ? 'mode-d1' : 'mode-backfill'}">
				<h2>Modo Atual</h2>
				<div class="value">${modeEmoji} ${modeLabel}</div>
				<div class="sub">Data: ${state.current.date}</div>
			</div>

			<div class="card">
				<h2>Progresso do Dia</h2>
				<div class="value">${progress}/${total}</div>
				<div class="progress-bar">
					<div class="progress-fill" style="width: ${pct}%">${pct}%</div>
				</div>
				<div class="sub">${state.current.records.toLocaleString('pt-BR')} comunicações</div>
			</div>

			<div class="card">
				<h2>Total Arquivado</h2>
				<div class="value">${state.stats.total_records.toLocaleString('pt-BR')}</div>
				<div class="sub">${state.stats.total_days_archived} dias completos</div>
			</div>

			<div class="card">
				<h2>Backfill</h2>
				<div class="value">${state.backfill.completed_dates.length} dias</div>
				<div class="sub">Alvo: ${state.backfill.oldest_target}</div>
			</div>
		</div>

		<div class="card">
			<h2>Tribunais - ${state.current.date}</h2>
			<div class="tribunais">
				${state.current.tribunais_done.map(t => `<span class="tribunal done">✓ ${t}</span>`).join('')}
				${state.current.tribunais_pending.map(t => `<span class="tribunal pending">${t}</span>`).join('')}
			</div>
		</div>

		<footer>
			Última execução: ${new Date(state.stats.last_run).toLocaleString('pt-BR')} | Auto-refresh: 30s
		</footer>
	</div>
</body>
</html>`;
}

interface TribunalSummary {
	tribunal: string;
	total_dates: number;
	total_records: number;
	total_bytes: number;
	oldest_date: string | null;
	newest_date: string | null;
}

interface TribunalDetail {
	tribunal: string;
	dates: {
		date: string;
		records: number;
		bytes: number;
		version: number;
		hash: string;
	}[];
}

async function listTribunaisData(env: Env): Promise<{ tribunais: TribunalSummary[]; last_updated: string }> {
	const tribunaisMap = new Map<string, TribunalSummary>();

	// Initialize all tribunals
	for (const t of TRIBUNAIS) {
		tribunaisMap.set(t, {
			tribunal: t,
			total_dates: 0,
			total_records: 0,
			total_bytes: 0,
			oldest_date: null,
			newest_date: null
		});
	}

	// List all objects in R2
	let cursor: string | undefined;
	do {
		const listed = await env.DJEN_STORAGE.list({ prefix: 'cadernos/', cursor, limit: 1000 });

		for (const obj of listed.objects) {
			// Parse key: cadernos/2026-01-21/TJSP-D-2026-01-21_v1.zip
			const match = obj.key.match(/cadernos\/(\d{4}-\d{2}-\d{2})\/([A-Z0-9]+)-D-/);
			if (!match) continue;

			const [, date, tribunal] = match;
			const summary = tribunaisMap.get(tribunal);
			if (!summary) continue;

			summary.total_dates += 1;
			summary.total_bytes += obj.size;

			// Get records from custom metadata if available
			if (obj.customMetadata?.total_comunicacoes) {
				summary.total_records += parseInt(obj.customMetadata.total_comunicacoes, 10);
			}

			if (!summary.oldest_date || date < summary.oldest_date) {
				summary.oldest_date = date;
			}
			if (!summary.newest_date || date > summary.newest_date) {
				summary.newest_date = date;
			}
		}

		cursor = listed.truncated ? listed.cursor : undefined;
	} while (cursor);

	return {
		tribunais: Array.from(tribunaisMap.values()).sort((a, b) => b.total_records - a.total_records),
		last_updated: new Date().toISOString()
	};
}

async function getTribunalDetails(env: Env, tribunal: string): Promise<TribunalDetail> {
	const dates: TribunalDetail['dates'] = [];

	let cursor: string | undefined;
	do {
		const listed = await env.DJEN_STORAGE.list({ prefix: 'cadernos/', cursor, limit: 1000 });

		for (const obj of listed.objects) {
			// Parse key: cadernos/2026-01-21/TJSP-D-2026-01-21_v1.zip
			const match = obj.key.match(/cadernos\/(\d{4}-\d{2}-\d{2})\/([A-Z0-9]+)-D-.*_v(\d+)\.zip/);
			if (!match) continue;

			const [, date, objTribunal, version] = match;
			if (objTribunal !== tribunal) continue;

			dates.push({
				date,
				records: obj.customMetadata?.total_comunicacoes ? parseInt(obj.customMetadata.total_comunicacoes, 10) : 0,
				bytes: obj.size,
				version: parseInt(version, 10),
				hash: obj.customMetadata?.hash || ''
			});
		}

		cursor = listed.truncated ? listed.cursor : undefined;
	} while (cursor);

	return {
		tribunal,
		dates: dates.sort((a, b) => b.date.localeCompare(a.date))
	};
}
