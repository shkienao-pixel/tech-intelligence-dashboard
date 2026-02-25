/**
 * i18n — Chinese / English UI translations
 * Usage:
 *   Include this file before other scripts.
 *   Add data-i18n="key" to any element whose textContent should be translated.
 *   Add data-i18n-ph="key" to inputs whose placeholder should be translated.
 *   Call applyLang() once on DOMContentLoaded (done automatically below).
 */

const I18N = {
  en: {
    /* ── Navigation ── */
    'nav.dashboard':   'Dashboard',
    'nav.reports':     'Reports',
    'nav.influencers': 'Influencers',
    'nav.settings':    'Settings',
    'nav.dark':        'Dark Mode',
    'nav.light':       'Light Mode',
    'nav.lang':        '中文',

    /* ── Sidebar brand ── */
    'brand.subtitle': 'INFLUENCER ENGINE',

    /* ── Dashboard ── */
    'dash.title':           "Today's Intelligence Summary",
    'dash.subtitle':        'Real-time X signal monitoring · 100 top tech influencers',
    'dash.generate':        'Generate Daily Report',
    'stat.monitored':       'Influencers Monitored',
    'stat.posts':           'Posts Analyzed Today',
    'stat.signals':         'Emerging Signals',
    'stat.live':            'Live',
    'stat.last24':          'last 24 hours',
    'stat.vs_week':         'vs last week',
    'stat.new_today':       'New Today',
    'trending.title':       'Trending Topics',
    'trending.live':        'Live',
    'trending.velocity':    'Velocity Insights',
    'reports.title':        'Recent Reports',
    'reports.view_all':     'View All',
    'reports.load_older':   'Load Older Archives',
    'reports.col.name':     'Report Name',
    'reports.col.date':     'Date',
    'reports.col.score':    'Score',
    'reports.col.actions':  'Actions',
    'reports.waiting':        'Waiting for first report…',
    'reports.waiting_hint':   'Click "Generate Daily Report" to fetch live data',
    'reports.delete_confirm': 'Delete this report? This action cannot be undone.',
    'reports.deleted':        'Report deleted.',
    'reports.delete_failed':  'Delete failed',
    'status.checking':        'Status: Checking…',
    'status.ready':         'Status: Ready',
    'status.setup':         'Status: Setup Required',
    'status.offline':       'Status: Offline (Demo Mode)',

    /* ── Influencers page ── */
    'inf.title':       'Influencer Management',
    'inf.subtitle':    'Manage the X accounts monitored for daily intelligence reports.',
    'inf.add_title':   'Add Influencer',
    'inf.add_btn':     'Add to List',
    'inf.adding':      'Adding…',
    'inf.search_ph':   'Search influencers…',
    'inf.add_ph':      'username (e.g. karpathy)',
    'inf.view_x':      'View on X',
    'inf.empty':       'No influencers found',

    /* ── Settings page ── */
    'set.title':             'Settings',
    'set.subtitle':          'Configure the intelligence pipeline and connection credentials.',
    'set.conn_title':        'Connection Status',
    'set.checked':           'Checked',
    'set.backend':           'Backend',
    'set.x_account':         'X Account',
    'set.claude':            'Claude API',
    'set.online':            'Online',
    'set.offline':           'Offline',
    'set.not_configured':    'Not configured',
    'set.api_key_set':       'API Key set',
    'set.cred_hint':         'API credentials are stored in server/.env. Edit that file to update X_USERNAME, X_PASSWORD, and ANTHROPIC_API_KEY.',
    'set.data_title':        'Data Overview',
    'set.reports_saved':     'Reports Saved',
    'set.inf_tracked':       'Influencers Tracked',
    'set.fetch_title':       'Report Generation Parameters',
    'set.hours_label':       'Lookback Window (hours)',
    'set.hours_hint':        'How many hours back to scan posts (default: 24)',
    'set.max_label':         'Max Posts Per Influencer',
    'set.max_hint':          'Maximum posts fetched per account per run (default: 20)',
    'set.save':              'Save Settings',
    'set.saving':            'Saving…',
    'set.cred_title':        'Credential Setup',
    'set.cred_desc':         'To enable live X data collection, edit server/.env and fill in your X account credentials and Anthropic API key. Then restart the backend with start.bat.',
    'set.get_key':           'Get Anthropic API key',

    /* ── Report page ── */
    'rep.back':      'Dashboard',
    'rep.overview':  'Overview',
    'rep.trends':    'Trends',
    'rep.inf':       'Influencers',
    'rep.download':  'Download PDF',
    'rep.export':    'Export Image',

    /* ── Offline banner ── */
    'banner.dash': '⚡ Demo Mode — Backend offline. Run start.bat to enable live X data.',
    'banner.inf':  '⚡ Demo Mode — Backend offline. Run start.bat to manage influencers.',
    'banner.set':  '⚡ Demo Mode — Backend offline. Run start.bat to configure settings.',
  },

  zh: {
    /* ── Navigation ── */
    'nav.dashboard':   '仪表盘',
    'nav.reports':     '报告',
    'nav.influencers': '博主管理',
    'nav.settings':    '设置',
    'nav.dark':        '深色模式',
    'nav.light':       '浅色模式',
    'nav.lang':        'EN',

    /* ── Sidebar brand ── */
    'brand.subtitle': '博主情报引擎',

    /* ── Dashboard ── */
    'dash.title':           '今日情报摘要',
    'dash.subtitle':        'X 平台实时信号监控 · 100 位顶尖科技博主',
    'dash.generate':        '生成每日报告',
    'stat.monitored':       '监控博主数',
    'stat.posts':           '今日分析推文',
    'stat.signals':         '新兴信号',
    'stat.live':            '实时',
    'stat.last24':          '过去 24 小时',
    'stat.vs_week':         '对比上周',
    'stat.new_today':       '今日新增',
    'trending.title':       '热门话题',
    'trending.live':        '实时',
    'trending.velocity':    '热度趋势',
    'reports.title':        '近期报告',
    'reports.view_all':     '查看全部',
    'reports.load_older':   '加载更早存档',
    'reports.col.name':     '报告名称',
    'reports.col.date':     '日期',
    'reports.col.score':    '评级',
    'reports.col.actions':  '操作',
    'reports.waiting':        '等待第一份报告…',
    'reports.waiting_hint':   '点击"生成每日报告"拉取实时数据',
    'reports.delete_confirm': '确认删除这份报告？此操作不可撤销。',
    'reports.deleted':        '报告已删除。',
    'reports.delete_failed':  '删除失败',
    'status.checking':        '状态：检查中…',
    'status.ready':         '状态：就绪',
    'status.setup':         '状态：需要配置',
    'status.offline':       '状态：离线（演示模式）',

    /* ── Influencers page ── */
    'inf.title':       '博主管理',
    'inf.subtitle':    '管理每日情报报告中监控的 X 账号。',
    'inf.add_title':   '添加博主',
    'inf.add_btn':     '加入列表',
    'inf.adding':      '添加中…',
    'inf.search_ph':   '搜索博主…',
    'inf.add_ph':      '用户名（如 karpathy）',
    'inf.view_x':      '在 X 上查看',
    'inf.empty':       '未找到博主',

    /* ── Settings page ── */
    'set.title':             '设置',
    'set.subtitle':          '配置情报采集流程与连接凭据。',
    'set.conn_title':        '连接状态',
    'set.checked':           '检查于',
    'set.backend':           '后端服务',
    'set.x_account':         'X 账号',
    'set.claude':            'Claude API',
    'set.online':            '在线',
    'set.offline':           '离线',
    'set.not_configured':    '未配置',
    'set.api_key_set':       'API Key 已设置',
    'set.cred_hint':         'API 凭据存储在 server/.env。编辑该文件以更新 X_USERNAME、X_PASSWORD 和 ANTHROPIC_API_KEY。',
    'set.data_title':        '数据概览',
    'set.reports_saved':     '已保存报告',
    'set.inf_tracked':       '追踪博主数',
    'set.fetch_title':       '报告生成参数',
    'set.hours_label':       '回溯时间窗口（小时）',
    'set.hours_hint':        '向前抓取多少小时的推文（默认：24）',
    'set.max_label':         '每位博主最大帖子数',
    'set.max_hint':          '每次运行每个账号最多抓取的帖子数（默认：20）',
    'set.save':              '保存设置',
    'set.saving':            '保存中…',
    'set.cred_title':        '凭据配置',
    'set.cred_desc':         '如需启用 X 实时数据，请编辑 server/.env 填写 X 账号凭据和 Anthropic API Key，然后用 start.bat 重启后端。',
    'set.get_key':           '获取 Anthropic API Key',

    /* ── Report page ── */
    'rep.back':      '仪表盘',
    'rep.overview':  '概览',
    'rep.trends':    '趋势',
    'rep.inf':       '博主',
    'rep.download':  '下载 PDF',
    'rep.export':    '导出图片',

    /* ── Offline banner ── */
    'banner.dash': '⚡ 演示模式 — 后端离线。运行 start.bat 以启用实时 X 数据。',
    'banner.inf':  '⚡ 演示模式 — 后端离线。运行 start.bat 以管理博主。',
    'banner.set':  '⚡ 演示模式 — 后端离线。运行 start.bat 以配置设置。',
  },
};

// ── Core API ──────────────────────────────────────────────────────────────────
let _lang = localStorage.getItem('lang') || 'zh';

/** Translate a key, falling back to English then the key itself. */
function t(key) {
  return I18N[_lang]?.[key] ?? I18N.en[key] ?? key;
}

/** Apply translations to all data-i18n / data-i18n-ph elements. */
function applyLang(lang) {
  _lang = lang;
  localStorage.setItem('lang', lang);

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const v = I18N[lang]?.[el.dataset.i18n];
    if (v !== undefined) el.textContent = v;
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const v = I18N[lang]?.[el.dataset.i18nPh];
    if (v !== undefined) el.placeholder = v;
  });
  // Update every lang-toggle button label
  document.querySelectorAll('[data-lang-toggle]').forEach(btn => {
    btn.textContent = lang === 'zh' ? 'EN' : '中文';
  });

  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
}

function toggleLang() {
  applyLang(_lang === 'zh' ? 'en' : 'zh');
}

// Auto-apply on first load
document.addEventListener('DOMContentLoaded', () => applyLang(_lang));
