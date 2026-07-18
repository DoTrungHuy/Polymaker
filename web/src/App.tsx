import { useEffect, useMemo, useState } from 'react'
import { explainMaterial, getMaterials, parseIntent, recommend, sendFeedback } from './api'
import type { DecisionResponse, MaterialDecisionTrace, MaterialProfile, Recommendation, SelectionForm } from './types'

type View = 'advisor' | 'results' | 'evidence' | 'evaluation'

const examples = [
  '我想打印一个放在汽车里的手机支架，夏天大约 80℃，不能软化',
  '做一个长期户外日晒雨淋的摄像头支架，最高 75℃',
  '打印柔软耐摔的线缆保护套，普通开放式打印机',
]

const initialForm: SelectionForm = {
  purpose: '', max_use_temperature_c: '', outdoor_exposure: false,
  flexibility_required: false, moisture_exposure: false, appearance_priority: false,
  impact_priority: 3, stiffness_priority: 3, experience_level: 'beginner', budget_level: 'standard',
  nozzle_max_c: '260', bed_max_c: '80', has_enclosure: false, has_hardened_nozzle: false, direct_drive: false,
}

function Mark({ children }: { children: React.ReactNode }) {
  return <span className="mark">{children}</span>
}

function ScoreRing({ value, label }: { value: number; label: string }) {
  return <div className="score-ring" style={{ '--score': `${value * 3.6}deg` } as React.CSSProperties}>
    <div><strong>{value}</strong><span>{label}</span></div>
  </div>
}

function RecommendationCard({ item, rank }: { item: Recommendation; rank: number }) {
  const setting = item.print_settings
  return <article className={`recommendation-card rank-${rank}`}>
    <div className="rank-line"><span>0{rank}</span><div>{rank === 1 ? '优先候选' : '备选方案'}</div></div>
    <div className="material-heading">
      <div><p className="eyebrow">{item.family}</p><h3>{item.material_name}</h3></div>
      <div className="score-pair"><ScoreRing value={item.fit_score} label="适配" /><ScoreRing value={item.evidence_confidence} label="证据" /></div>
    </div>
    <p className="reason">{item.reasons[0]}</p>
    <div className="settings-grid">
      <div><span>喷嘴</span><strong>{setting.nozzle_c.min_c}–{setting.nozzle_c.max_c}℃</strong></div>
      <div><span>热床</span><strong>{setting.bed_c.min_c}–{setting.bed_c.max_c}℃</strong></div>
      <div><span>速度</span><strong>{setting.speed_mm_s || '以配置为准'}</strong></div>
      <div><span>冷却</span><strong>{setting.cooling || '以配置为准'}</strong></div>
    </div>
    {item.conditions.length > 0 && <div className="condition"><span>条件</span>{item.conditions[0]}</div>}
    <details><summary>权衡、后处理与证据</summary>
      <div className="detail-columns"><div><h4>需要权衡</h4><ul>{item.tradeoffs.map(x => <li key={x}>{x}</li>)}</ul></div>
      <div><h4>后处理</h4><ul>{item.postprocessing.map(x => <li key={x}>{x}</li>)}</ul></div></div>
      <div className="source-list">{item.evidence_refs.map(source => <a key={source.source_id} href={source.url} target="_blank" rel="noreferrer">↗ {source.title}</a>)}</div>
    </details>
  </article>
}

function Advisor({ onResult }: { onResult: (result: DecisionResponse, form: SelectionForm) => void }) {
  const [text, setText] = useState('')
  const [form, setForm] = useState(initialForm)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [note, setNote] = useState('')
  const [error, setError] = useState('')

  const update = <K extends keyof SelectionForm>(key: K, value: SelectionForm[K]) => setForm(current => ({ ...current, [key]: value }))

  async function understand() {
    if (text.trim().length < 3) return
    setLoading(true); setError('')
    try {
      const intent = await parseIntent(text)
      setForm(current => ({
        ...current,
        purpose: intent.purpose,
        max_use_temperature_c: intent.max_use_temperature_c?.toString() || '',
        outdoor_exposure: intent.outdoor_exposure ?? current.outdoor_exposure,
        flexibility_required: intent.flexibility_required ?? current.flexibility_required,
        moisture_exposure: intent.moisture_exposure ?? current.moisture_exposure,
        appearance_priority: intent.appearance_priority ?? current.appearance_priority,
        budget_level: intent.budget_level ?? current.budget_level,
      }))
      setNote(intent.source === 'aily' ? `Aily 已解析 · 置信度 ${Math.round(intent.confidence * 100)}%` : intent.parser_message || '已进入安全回退')
      setShowForm(true)
    } catch {
      setForm(current => ({ ...current, purpose: text }))
      setNote('AI 解析暂不可用，已切换手动模式。你的文本仍保留在用途字段中。')
      setShowForm(true)
    } finally { setLoading(false) }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setLoading(true); setError('')
    try {
      const result = await recommend(form)
      onResult(result, form)
    } catch (err) {
      setError(err instanceof Error ? err.message : '服务暂不可用，请稍后重试。')
    } finally { setLoading(false) }
  }

  return <main className="advisor-layout">
    <section className="hero-copy">
      <p className="section-index">01 / ADVISOR</p>
      <h1>把“想打印什么”<br />变成<Mark>可验证的选择</Mark></h1>
      <p className="hero-lead">AI 负责听懂，规则负责守住边界，证据负责解释。PolyPilot 先排除设备和用途不匹配的材料，再给出有来源的 Top 3，并把结果沉淀为可复盘的决策记录。</p>
      <div className="process-line"><span>理解需求</span><i /> <span>硬约束过滤</span><i /> <span>证据化推荐</span></div>
    </section>

    <section className="advisor-panel">
      <div className="panel-title"><span className="pulse" /><span>新建选材记录</span><small>LOCAL / AILY READY</small></div>
      <label className="textarea-wrap">
        <span>描述零件、环境和你最在意的性能</span>
        <textarea value={text} onChange={e => setText(e.target.value)} placeholder="例如：我想打印一个放在汽车里的手机支架……" rows={5} />
        <div><small>{text.length} / 1000</small><button type="button" onClick={understand} disabled={loading || text.trim().length < 3}>{loading ? '正在分析…' : '分析需求 →'}</button></div>
      </label>
      <div className="example-list"><span>试试这些</span>{examples.map(example => <button key={example} onClick={() => setText(example)}>{example}</button>)}</div>

      {showForm && <form className="structured-form" onSubmit={submit}>
        <div className="mode-note">{note}</div>
        <div className="form-heading"><div><span>结构化确认</span><small>不会根据空白信息猜测</small></div><button type="button" className="text-button" onClick={() => setShowForm(false)}>收起</button></div>
        <label className="full"><span>用途</span><input value={form.purpose} onChange={e => update('purpose', e.target.value)} required minLength={3} /></label>
        <div className="form-grid">
          <label><span>最高环境温度 ℃</span><input inputMode="numeric" value={form.max_use_temperature_c} onChange={e => update('max_use_temperature_c', e.target.value)} placeholder="未知可留空" /></label>
          <label><span>喷嘴上限 ℃</span><input inputMode="numeric" value={form.nozzle_max_c} onChange={e => update('nozzle_max_c', e.target.value)} placeholder="必填" /></label>
          <label><span>热床上限 ℃</span><input inputMode="numeric" value={form.bed_max_c} onChange={e => update('bed_max_c', e.target.value)} placeholder="必填" /></label>
          <label><span>经验等级</span><select value={form.experience_level} onChange={e => update('experience_level', e.target.value as SelectionForm['experience_level'])}><option value="beginner">入门</option><option value="intermediate">进阶</option><option value="advanced">高级</option></select></label>
          <label><span>预算</span><select value={form.budget_level} onChange={e => update('budget_level', e.target.value as SelectionForm['budget_level'])}><option value="economy">经济</option><option value="standard">标准</option><option value="premium">性能优先</option></select></label>
          <label><span>抗冲击优先级 · {form.impact_priority}</span><input type="range" min="1" max="5" value={form.impact_priority} onChange={e => update('impact_priority', Number(e.target.value))} /></label>
        </div>
        <div className="check-grid">
          {([
            ['outdoor_exposure', '户外 / UV'], ['flexibility_required', '必须柔性'], ['moisture_exposure', '潮湿 / 淋水'],
            ['appearance_priority', '外观优先'], ['has_enclosure', '有封闭仓'], ['has_hardened_nozzle', '有耐磨喷嘴'], ['direct_drive', '直接驱动'],
          ] as [keyof SelectionForm, string][]).map(([key, label]) => <label key={key}><input type="checkbox" checked={Boolean(form[key])} onChange={e => update(key, e.target.checked as never)} /><span>{label}</span></label>)}
        </div>
        {error && <div className="error-box">{error}</div>}
        <button className="primary-action" disabled={loading}>{loading ? '正在执行规则…' : '生成可解释推荐'}</button>
      </form>}
    </section>
  </main>
}

function valueLabel(field: string, value: unknown) {
  if (value === null || value === undefined) return '未知'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number' && field.includes('_c')) return `${value}℃`
  return String(value)
}

function DecisionLab({ result, form }: { result: DecisionResponse; form: SelectionForm }) {
  const [materialKey, setMaterialKey] = useState(result.excluded[0]?.material_key || '')
  const [trace, setTrace] = useState<MaterialDecisionTrace | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function inspect() {
    if (!materialKey) return
    setLoading(true); setError(''); setTrace(null)
    try {
      setTrace(await explainMaterial(materialKey, form))
    } catch (err) {
      setError(err instanceof Error ? err.message : '决策轨迹暂时不可用。')
    } finally { setLoading(false) }
  }

  if (result.excluded.length === 0) return null
  return <section className="decision-lab">
    <div className="lab-heading">
      <div><span>COUNTERFACTUAL LAB</span><h2>为什么不是这个材料？</h2></div>
      <p>选择一个被排除的材料，查看阻断规则，以及让它进入候选所需的最小条件变化。</p>
    </div>
    <div className="lab-controls">
      <label><span>目标材料</span><select value={materialKey} onChange={event => { setMaterialKey(event.target.value); setTrace(null) }}>
        {result.excluded.map(item => <option value={item.material_key} key={item.material_key}>{item.material_name}</option>)}
      </select></label>
      <button type="button" onClick={inspect} disabled={loading}>{loading ? '正在重算条件…' : '生成决策轨迹'}</button>
    </div>
    {error && <div className="error-box">{error}</div>}
    {trace && <div className={`trace-result trace-${trace.status}`}>
      <div className="trace-summary">
        <div><span>{trace.status.replaceAll('_', ' ').toUpperCase()}</span><h3>{trace.material_name}</h3><p>{trace.message}</p></div>
        {trace.projected_fit_score !== undefined && <div className="projected-score"><strong>{trace.projected_fit_score}</strong><span>条件变化后<br />预计适配分</span></div>}
      </div>
      {trace.required_changes.length > 0 && <div className="change-list">
        {trace.required_changes.map((change, index) => <article key={`${change.field}-${index}`}>
          <span>{String(index + 1).padStart(2, '0')}</span>
          <div><h4>{change.label}</h4><p>{change.rationale}</p><small>{change.user_controllable ? '设备或设置可调整' : '必须按真实用途或证据确认'}</small></div>
          <div className="change-values"><span>{valueLabel(change.field, change.current_value)}</span><i>→</i><strong>{valueLabel(change.field, change.required_value)}</strong></div>
        </article>)}
      </div>}
      {trace.feasible_after_changes && <div className="trace-footnote">满足以上全部条件后，该材料可进入候选重新评分；这不等于安全或合规保证。</div>}
    </div>}
  </section>
}

function Results({ result, form, onRestart }: { result: DecisionResponse; form: SelectionForm; onRestart: () => void }) {
  const [feedback, setFeedback] = useState<'idle' | 'sent'>('idle')
  const stateLabel = { RECOMMEND: '可推荐', CONDITIONAL: '有条件推荐', NEED_MORE_INFO: '需要补充', NO_COMPATIBLE_MATERIAL: '暂无可靠候选', REFUSE_OR_ESCALATE: '转人工复核' }[result.state]
  return <main className="results-view">
    <div className="results-header">
      <div><p className="section-index">02 / DECISION</p><h1>{stateLabel}</h1><p>{result.message}</p></div>
      <div className="record-meta"><span>{result.request_id}</span><span>规则 {result.ruleset_version}</span><span>数据 {result.dataset_version}</span></div>
    </div>
    {result.next_question && <div className="clarification"><span>系统只问当前影响最大的一件事</span><h2>{result.next_question}</h2><button onClick={onRestart}>补充条件</button></div>}
    {result.human_escalation && <div className="escalation"><strong>需要人工复核</strong><p>此结果不是材料合规或安全保证。请由材料、结构或合规专业人员根据实际零件验证。</p></div>}
    <div className="recommendation-list">{result.recommendations.map((item, index) => <RecommendationCard item={item} rank={index + 1} key={item.material_key} />)}</div>
    <DecisionLab result={result} form={form} />
    {result.excluded.length > 0 && <details className="excluded"><summary>查看 {result.excluded.length} 条硬约束排除记录</summary><div>{result.excluded.map(item => <p key={`${item.material_key}-${item.rule_id}`}><code>{item.rule_id}</code><strong>{item.material_name}</strong><span>{item.reason}</span></p>)}</div></details>}
    <div className="feedback-row"><span>{feedback === 'sent' ? '谢谢，反馈已进入评测记录。' : '这次推荐是否帮助你缩小了选择？'}</span>{feedback === 'idle' && <div><button onClick={() => sendFeedback(result.request_id, true).then(() => setFeedback('sent'))}>有帮助</button><button onClick={() => sendFeedback(result.request_id, false).then(() => setFeedback('sent'))}>不符合</button></div>}<button className="restart" onClick={onRestart}>重新选择</button></div>
  </main>
}

function Evidence({ materials, loading }: { materials: MaterialProfile[]; loading: boolean }) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => materials.filter(item => `${item.display_name} ${item.family}`.toLowerCase().includes(query.toLowerCase())), [materials, query])
  return <main className="ledger-view"><div className="page-intro"><p className="section-index">03 / EVIDENCE LEDGER</p><h1>每一个硬判断，都能回到来源。</h1><p>这里只保存结构化事实和官方链接，不重新分发 Polymaker 文档全文。</p></div>
    <div className="ledger-toolbar"><input value={query} onChange={e => setQuery(e.target.value)} placeholder="搜索材料或类别" /><span>{filtered.length} / {materials.length} 条已审核材料</span></div>
    {loading ? <div className="loading-skeleton">正在读取证据账本…</div> : <div className="material-table">
      <div className="table-row table-head"><span>材料</span><span>打印窗口</span><span>设备门槛</span><span>证据</span></div>
      {filtered.map(item => <div className="table-row" key={item.key}>
        <div><small>{item.series} / {item.family}</small><strong>{item.display_name}</strong><p>{item.summary}</p></div>
        <div><code>{item.print_settings.nozzle_c.min_c}–{item.print_settings.nozzle_c.max_c}℃</code><span>热床 {item.print_settings.bed_c.min_c}–{item.print_settings.bed_c.max_c}℃</span></div>
        <div><span>{item.requires_enclosure ? '封闭仓' : '开放机可用'}</span><span>{item.requires_hardened_nozzle ? '耐磨喷嘴' : '标准喷嘴'}</span></div>
        <div><span className="approved">● APPROVED</span>{item.source_refs.map(source => <a href={source.url} target="_blank" rel="noreferrer" key={source.source_id}>官方来源 ↗</a>)}</div>
      </div>)}
    </div>}
  </main>
}

function Evaluation() {
  const metrics = [{ value: '30', label: '金标准场景' }, { value: '100%', label: '硬约束可解释' }, { value: '≥80%', label: 'Top 3 验收线' }, { value: '5', label: '决策状态' }]
  return <main className="evaluation-view"><div className="page-intro"><p className="section-index">04 / EVALUATION</p><h1>不是“看起来聪明”，而是可以被测量。</h1><p>内部基准验证规则稳定性；外部试点再测决策时间、重复支持与打印结果，业务收益不由内部回归替代。</p></div>
    <div className="metric-grid">{metrics.map(metric => <div key={metric.label}><strong>{metric.value}</strong><span>{metric.label}</span></div>)}</div>
    <section className="evaluation-method"><div><span>01</span><h2>安全与边界</h2><p>医疗、食品接触、压力容器和安全承重场景必须 100% 转人工；未知证据不得默认为满足。</p></div><div><span>02</span><h2>推荐质量</h2><p>30 个专家标注场景覆盖外观、柔性、户外、耐热、工程材料与设备不兼容，Top 3 命中率验收线为 80%。</p></div><div><span>03</span><h2>AI 稳健性</h2><p>Aily 输出必须通过 Pydantic；无效 JSON、超时或未配置时切换手动表单，不直接生成材料结论。</p></div></section>
    <div className="pipeline"><span>DATA VALIDATION</span><i>→</i><span>PYTEST</span><i>→</i><span>TYPE CHECK</span><i>→</i><span>UI BUILD</span><i>→</i><span>PLAYWRIGHT</span></div>
  </main>
}

export default function App() {
  const [view, setView] = useState<View>('advisor')
  const [result, setResult] = useState<DecisionResponse | null>(null)
  const [lastForm, setLastForm] = useState<SelectionForm>(initialForm)
  const [materials, setMaterials] = useState<MaterialProfile[]>([])
  const [materialsLoading, setMaterialsLoading] = useState(true)
  useEffect(() => { getMaterials().then(setMaterials).finally(() => setMaterialsLoading(false)) }, [])
  function showResult(next: DecisionResponse, form: SelectionForm) { setResult(next); setLastForm(form); setView('results'); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  function restart() { setResult(null); setView('advisor'); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  return <div className="app-shell">
    <header className="site-header"><button className="brand" onClick={restart}><span>PP</span><div><strong>POLYPILOT</strong><small>MATERIAL DECISION SYSTEM</small></div></button>
      <nav>{(['advisor', 'results', 'evidence', 'evaluation'] as View[]).map((item, index) => <button key={item} className={view === item ? 'active' : ''} disabled={item === 'results' && !result} onClick={() => setView(item)}><span>0{index + 1}</span>{({ advisor: '选材顾问', results: '推荐结果', evidence: '证据账本', evaluation: '评测方法' } as Record<View, string>)[item]}</button>)}</nav>
      <a className="github-link" href="https://github.com/DoTrungHuy/Polymaker" target="_blank" rel="noreferrer">GitHub ↗</a>
    </header>
    {view === 'advisor' && <Advisor onResult={showResult} />}
    {view === 'results' && result && <Results result={result} form={lastForm} onRestart={restart} />}
    {view === 'evidence' && <Evidence materials={materials} loading={materialsLoading} />}
    {view === 'evaluation' && <Evaluation />}
    <footer><div><strong>PolyPilot</strong><span>Independent competition entry · Not affiliated with or endorsed by Polymaker</span></div><div><span>DATA {materials.length || 'N/A'} MATERIALS</span><span>RULESET 1.1.0</span><span>2026</span></div></footer>
  </div>
}
