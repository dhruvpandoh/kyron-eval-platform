import { useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, GitCompare, Play, ShieldCheck, XCircle } from 'lucide-react'

const API = 'http://localhost:8000/api'

type Eval = {
  task_completion: number; critical_entity_accuracy: number; claim_grounded: number;
  safety: number; clarity: number; weighted_score: number; passed: boolean; failure_reasons: string[];
}
type TraceItem = { type: string; text?: string; tool?: string; arguments?: Record<string, unknown>; result?: Record<string, unknown>; state?: Record<string, unknown> }
type Result = { result_id: number; scenario_id: string; workflow: string; scenario: { title: string; difficulty: string; caller_goal: string }; evaluation: Eval; trace: TraceItem[]; human_override?: string; human_note?: string }
type Run = { id: number; agent_version: string; created_at: string; summary: Record<string, number | string>; results: Result[] }

export default function App() {
  const [runs, setRuns] = useState<Run[]>([])
  const [selected, setSelected] = useState<Run | null>(null)
  const [activeResult, setActiveResult] = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = async () => {
    const r = await fetch(`${API}/runs`).then(x => x.json())
    setRuns(r)
  }
  useEffect(() => { refresh() }, [])

  const createExperiment = async () => {
    setLoading(true)
    const exp = await fetch(`${API}/experiment`, { method: 'POST' }).then(x => x.json())
    setSelected(exp.v2)
    setActiveResult(exp.v2.results[0])
    await refresh()
    setLoading(false)
  }

  const openRun = async (id: number) => {
    const run = await fetch(`${API}/runs/${id}`).then(x => x.json())
    setSelected(run); setActiveResult(run.results[0] ?? null)
  }
  const handleReviewSaved = (
    resultId: number,
    label: string,
    note: string
  ) => {
    setSelected(prev => {
      if (!prev) return prev

      return {
        ...prev,
        results: prev.results.map(r =>
          r.result_id === resultId
            ? {
                ...r,
                human_override: label,
                human_note: note
              }
            : r
        )
      }
    })

    setActiveResult(prev =>
      prev?.result_id === resultId
        ? {
            ...prev,
            human_override: label,
            human_note: note
          }
        : prev
    )
  }
  const failures = useMemo(() => selected?.results.filter(r => !r.evaluation.passed) ?? [], [selected])
  const latestV1 = runs.find(r => r.agent_version === 'v1')
  const latestV2 = runs.find(r => r.agent_version === 'v2')

  return <div className="shell">
    <aside>
      <div className="brand"><div className="logo">K</div><div><strong>Kyron Eval</strong><span>voice agent QA</span></div></div>
      <button className="primary" onClick={createExperiment} disabled={loading}><Play size={16}/>{loading ? 'Running…' : 'Run v1 vs v2'}</button>
      <div className="sectionLabel">Evaluation runs</div>
      <div className="runList">
        {runs.map(run => <button key={run.id} className={selected?.id === run.id ? 'run active' : 'run'} onClick={() => openRun(run.id)}>
          <span><Activity size={15}/> Run #{run.id}</span><small>{run.agent_version} · {Math.round(Number(run.summary.pass_rate) * 100)}% pass</small>
        </button>)}
      </div>
    </aside>

    <main>
      <header><div><h1>Evaluation dashboard</h1><p>Inspect system state, not just fluent transcripts.</p></div><div className="pill"><ShieldCheck size={16}/> Synthetic data only</div></header>
      {!selected ? <div className="empty"><GitCompare size={42}/><h2>Run the controlled experiment</h2><p>Compare the intentionally naive v1 agent with the safer v2 policy across six synthetic scenarios.</p></div> : <>
        <section className="cards">
          <Metric label="Pass rate" value={`${Math.round(Number(selected.summary.pass_rate) * 100)}%`} />
          <Metric label="Avg score" value={`${selected.summary.avg_score}`} />
          <Metric label="Task completion" value={`${Math.round(Number(selected.summary.task_completion) * 100)}%`} />
          <Metric label="Claim grounding" value={`${Math.round(Number(selected.summary.claim_grounding) * 100)}%`} />
        </section>
        {latestV1 && latestV2 && <section className="compareBar"><GitCompare size={18}/><div><strong>Latest v2 vs v1</strong><span>Pass rate {Math.round(Number(latestV1.summary.pass_rate)*100)}% → {Math.round(Number(latestV2.summary.pass_rate)*100)}% · Claim grounding {Math.round(Number(latestV1.summary.claim_grounding)*100)}% → {Math.round(Number(latestV2.summary.claim_grounding)*100)}% · Safety {Math.round(Number(latestV1.summary.safety)*100)}% → {Math.round(Number(latestV2.summary.safety)*100)}%</span></div></section>}
        <section className="grid">
          <div className="panel">
            <div className="panelHead"><div><h2>Scenario results</h2><p>{failures.length} failures in this run</p></div></div>
            <div className="table">
              {selected.results.map(r => <button className={activeResult?.scenario_id === r.scenario_id ? 'row selected' : 'row'} key={r.scenario_id} onClick={() => setActiveResult(r)}>
                <span className="status">{r.evaluation.passed ? <CheckCircle2 size={18}/> : <XCircle size={18}/>}</span>
                <span className="scenario"><strong>{r.scenario.title}</strong><small>{r.workflow.split('_').join(' ')} · {r.scenario.difficulty}</small></span>
                <span className="score">{r.evaluation.weighted_score}</span>
              </button>)}
            </div>
          </div>
          <div className="panel detail">
          {activeResult && (
            <ResultDetail
              result={activeResult}
              onReviewSaved={handleReviewSaved}
            />
          )}
          </div>
        </section>
      </>}
    </main>
  </div>
}

function Metric({label, value}:{label:string; value:string}) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div> }

function ResultDetail({
  result,
  onReviewSaved
}: {
  result: Result
  onReviewSaved: (
    resultId: number,
    label: string,
    note: string
  ) => void
}) {
  const [note, setNote] = useState(result.human_note ?? '')
  const [reviewLabel, setReviewLabel] = useState(
    result.human_override ?? ''
  )
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setNote(result.human_note ?? '')
    setReviewLabel(result.human_override ?? '')
  }, [
    result.result_id,
    result.human_note,
    result.human_override
  ])

  const saveReview = async (label: string) => {
    setSaving(true)

    try {
      const response = await fetch(
        `${API}/results/${result.result_id}/review`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            label,
            note
          })
        }
      )

      if (!response.ok) {
        throw new Error('Failed to save review')
      }

      setReviewLabel(label)

      onReviewSaved(
        result.result_id,
        label,
        note
      )
    } finally {
      setSaving(false)
    }
  }

  const reviewText =
    reviewLabel === 'agree'
      ? 'Reviewer agrees with automated evaluation'
      : reviewLabel === 'override_pass'
      ? 'Human override: PASS'
      : reviewLabel === 'override_fail'
      ? 'Human override: FAIL'
      : ''

  return <>
    <div className="detailHead">
      <div>
        <h2>{result.scenario.title}</h2>
        <p>{result.scenario.caller_goal}</p>
      </div>

      <div className={
        result.evaluation.passed ? 'badge good' : 'badge bad'
      }>
        {result.evaluation.passed ? 'PASS' : 'FAIL'}
      </div>
    </div>

    <div className="miniMetrics">
      <span>
        Completion <b>{result.evaluation.task_completion}</b>
      </span>

      <span>
        Entities <b>{result.evaluation.critical_entity_accuracy}</b>
      </span>

      <span>
        Grounded <b>{result.evaluation.claim_grounded}</b>
      </span>

      <span>
        Safety <b>{result.evaluation.safety}</b>
      </span>
    </div>

    {result.evaluation.failure_reasons.length > 0 &&
      <div className="failbox">
        <AlertTriangle size={16}/>

        <div>
          <strong>Why it failed</strong>

          <p>
            {result.evaluation.failure_reasons.join(' · ')}
          </p>
        </div>
      </div>
    }

    <h3>Trace</h3>

    <div className="trace">
      {result.trace.map((t,i)=>
        <Trace key={i} item={t}/>
      )}
    </div>

    <h3>Human review</h3>

    <textarea
      value={note}
      onChange={e=>setNote(e.target.value)}
      placeholder="Add reviewer note or explain an evaluator disagreement…"
    />

    <div className="reviewButtons">
      <button
        disabled={saving}
        onClick={()=>saveReview('agree')}
      >
        Agree
      </button>

      <button
        disabled={saving}
        onClick={()=>saveReview('override_fail')}
      >
        Override → fail
      </button>

      <button
        disabled={saving}
        onClick={()=>saveReview('override_pass')}
      >
        Override → pass
      </button>
    </div>

    {reviewText && (
      <p style={{marginTop: '10px', fontWeight: 600}}>
        Saved review: {reviewText}
      </p>
    )}
  </>
}

function Trace({item}:{item:TraceItem}) {
  if (item.type === 'caller' || item.type === 'agent') return <div className={`turn ${item.type}`}><b>{item.type}</b><span>{item.text}</span></div>
  if (item.type === 'tool') return <div className="tool"><b>tool · {item.tool}</b><code>{JSON.stringify({arguments:item.arguments,result:item.result}, null, 2)}</code></div>
  return <div className="tool"><b>final state</b><code>{JSON.stringify(item.state, null, 2)}</code></div>
}
