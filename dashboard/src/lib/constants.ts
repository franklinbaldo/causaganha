// Tribunal groups as specified in site.specs.md
export const TRIBUNALS = {
    superiores: ['STF', 'STJ', 'TST', 'TSE', 'STM', 'CNJ'],
    trfs: ['TRF1', 'TRF2', 'TRF3', 'TRF4', 'TRF5', 'TRF6'],
    trts: [
        'TRT1', 'TRT2', 'TRT3', 'TRT4', 'TRT5', 'TRT6', 'TRT7', 'TRT8',
        'TRT9', 'TRT10', 'TRT11', 'TRT12', 'TRT13', 'TRT14', 'TRT15', 'TRT16',
        'TRT17', 'TRT18', 'TRT19', 'TRT20', 'TRT21', 'TRT22', 'TRT23', 'TRT24'
    ],
    tjs: [
        'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDFT', 'TJES',
        'TJGO', 'TJMA', 'TJMG', 'TJMS', 'TJMT', 'TJPA', 'TJPB', 'TJPE',
        'TJPI', 'TJPR', 'TJRJ', 'TJRN', 'TJRO', 'TJRR', 'TJRS', 'TJSC',
        'TJSE', 'TJSP', 'TJTO'
    ],
} as const;

export const ALL_TRIBUNALS = [
    ...TRIBUNALS.superiores,
    ...TRIBUNALS.trfs,
    ...TRIBUNALS.trts,
    ...TRIBUNALS.tjs,
];

// API endpoints
export const API = {
    IA_METADATA: (date: string) => `https://archive.org/metadata/djen-${date}`,
    IA_DETAILS: (date: string) => `https://archive.org/details/djen-${date}`,
    GH_RUNS: 'https://api.github.com/repos/franklinbaldo/causaganha/actions/runs?per_page=10',
    GH_ACTIONS: 'https://github.com/franklinbaldo/causaganha/actions',
} as const;

// Colors (matching tailwind.config.mjs)
export const COLORS = {
    success: '#22c55e',
    warning: '#eab308',
    error: '#ef4444',
    muted: '#6b7280',
    border: '#1e2d27',
} as const;

// Calendar levels (for heatmap intensity)
export const CALENDAR_COLORS = [
    'bg-border',           // Level 0: no data
    'bg-accent-green/20',  // Level 1: 1-25%
    'bg-accent-green/40',  // Level 2: 26-50%
    'bg-accent-green/70',  // Level 3: 51-75%
    'bg-accent-green',     // Level 4: 76-100%
] as const;

// Labels (Portuguese)
export const LABELS = {
    header: {
        title: 'causaganha',
        subtitle: 'Monitor do Pipeline DJEN',
    },
    status: {
        operational: 'Operacional',
        degraded: 'Degradado',
        failure: 'Falha',
    },
    metrics: {
        files: { title: 'Arquivos Hoje', subtitle: 'tribunais com dados' },
        size: { title: 'Volume Hoje', subtitle: 'dados brutos' },
        days: { title: 'Dias Arquivados', subtitle: 'no Internet Archive' },
        health: { title: 'Saúde do Pipeline', subtitle: 'últimas 10 runs' },
    },
    activity: {
        title: 'Atividade de Coleta',
        less: 'Menos',
        more: 'Mais',
        total: 'Total coletado',
        days: 'Dias com dados',
        biggest: 'Maior dia',
    },
    tribunals: {
        title: 'Status por Tribunal',
        groups: {
            superiores: 'Superiores',
            trfs: 'Tribunais Regionais Federais',
            trts: 'Tribunais Regionais do Trabalho',
            tjs: 'Tribunais de Justiça',
        },
        status: {
            ok: 'OK',
            absent: 'Vazio',
            error: 'Falha',
            pending: 'Pendente',
        },
    },
    runs: {
        title: 'Execuções Recentes',
        viewAll: 'Ver todas →',
    },
    days: {
        title: 'Últimos Dias',
        viewAll: 'Internet Archive →',
    },
    info: {
        title: 'O que é isso?',
        body: 'Este dashboard monitora a coleta diária de comunicações judiciais do DJEN (Diário de Justiça Eletrônico Nacional). Os dados são arquivados permanentemente no Internet Archive para possibilitar análises de performance jurídica.',
    },
    error: {
        loading: 'Não foi possível carregar',
    },
} as const;

// Refresh interval (5 minutes)
export const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

// Calendar weeks to show
export const CALENDAR_WEEKS = 16;
