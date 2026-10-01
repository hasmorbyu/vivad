import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import cytoscape, { type Core } from 'cytoscape'
import { api } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Field } from '../../components/ui'
import type { J } from '../../types'

const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v).trim()

const KIND_LABEL: Record<string, string> = {
  case: 'CASE', party: 'PARTY', claim: 'CLAIM', evidence: 'EVIDENCE', event: 'EVENT',
  contradiction: 'CONTRADICTION', law: 'LAW', hearing: 'HEARING', decision: 'DECISION',
}

function styleSheet(): cytoscape.StylesheetJson {
  const fg = css('--fg'), bg = css('--bg'), sub = css('--sub2'), mut = css('--mut')
  return [
    { selector: 'node', style: { shape: 'rectangle', 'background-color': bg, 'border-width': 1, 'border-color': fg, 'border-style': 'solid',
        label: 'data(label)', color: fg, 'font-family': 'Special Elite', 'font-size': 10, 'text-wrap': 'wrap', 'text-max-width': '140px',
        'text-valign': 'center', 'text-halign': 'center', width: 'label', height: 'label', padding: '6px' } },
    { selector: 'node[kind = "case"]', style: { 'border-width': 3 } },
    { selector: 'node[kind = "party"]', style: { 'border-width': 2, 'background-color': sub } },
    { selector: 'node[kind = "evidence"]', style: { 'border-style': 'solid', 'background-color': sub } },
    { selector: 'node[kind = "claim"]', style: { 'border-style': 'dashed' } },
    { selector: 'node[kind = "contradiction"]', style: { 'border-style': 'double', 'border-width': 4 } },
    { selector: 'node[kind = "law"]', style: { 'border-style': 'dotted' } },
    { selector: 'node:selected', style: { 'border-style': 'double', 'border-width': 6 } },
    { selector: '.dim', style: { opacity: 0.18 } },
    { selector: 'edge', style: { width: 1, 'line-color': fg, 'target-arrow-color': fg, 'target-arrow-shape': 'triangle', 'curve-style': 'bezier',
        label: 'data(label)', color: mut, 'font-family': 'Special Elite', 'font-size': 7, 'text-rotation': 'autorotate',
        'text-background-color': bg, 'text-background-opacity': 1, 'text-background-padding': '1px', 'arrow-scale': 0.7 } },
    { selector: 'edge:selected', style: { width: 3 } },
  ] as cytoscape.StylesheetJson
}

export default function Graph() {
  const { caseData } = useCase()
  const box = useRef<HTMLDivElement>(null)
  const cy = useRef<Core | null>(null)
  const [info, setInfo] = useState({ n: 0, e: 0 })
  const [kinds, setKinds] = useState<string[]>([])
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const [selected, setSelected] = useState<J>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const cid = caseData.id

  const toEls = (g: J) => [
    ...g.nodes.map((n: J) => ({ group: 'nodes' as const, data: n.data })),
    ...g.edges.map((e: J) => ({ group: 'edges' as const, data: e.data })),
  ]
  const layout = useCallback(() => {
    const w = box.current?.clientWidth || 1000, h = box.current?.clientHeight || 600
    cy.current?.layout({ name: 'cose', animate: false, randomize: true, nodeRepulsion: () => 16000, idealEdgeLength: () => 90,
      nodeOverlap: 12, gravity: 1.4, componentSpacing: 60, padding: 24, numIter: 2500,
      boundingBox: { x1: 0, y1: 0, w: w * 1.5, h: h * 1.5 } } as cytoscape.LayoutOptions).run()
  }, [])

  const load = useCallback(async () => {
    if (!box.current) return
    setBusy(true); setErr('')
    try {
      const g = await api.get(`/cases/${cid}/graph`)
      if (!cy.current) {
        cy.current = cytoscape({ container: box.current, elements: [], style: styleSheet(), wheelSensitivity: 0.25, minZoom: 0.1, maxZoom: 3 })
        cy.current.on('tap', 'node', (ev) => {
          const d = ev.target.data()
          setSelected(d)
          cy.current?.elements().removeClass('dim')
          cy.current?.elements().not(ev.target.closedNeighborhood()).addClass('dim')
        })
        cy.current.on('tap', (ev) => { if (ev.target === cy.current) { setSelected(null); cy.current?.elements().removeClass('dim') } })
      }
      cy.current.elements().remove()
      cy.current.add(toEls(g))
      cy.current.resize()
      layout()
      cy.current.fit(undefined, 30)
      setInfo({ n: g.nodes.length, e: g.edges.length })
      setKinds([...new Set<string>(g.nodes.map((n: J) => n.data.kind))].sort())
      setHidden(new Set())
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }, [cid, layout])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const ro = new ResizeObserver(() => cy.current?.resize())
    if (box.current) ro.observe(box.current)
    return () => { ro.disconnect(); cy.current?.destroy(); cy.current = null }
  }, [])
  useEffect(() => {
    const c = cy.current
    if (!c) return
    c.batch(() => c.nodes().forEach((n) => { n.style('display', hidden.has(n.data('kind')) ? 'none' : 'element') }))
  }, [hidden, info])

  const deepLink = useMemo(() => {
    if (!selected) return null
    if (selected.evidence_id) return { to: `/cases/${cid}/evidence/${selected.evidence_id}`, text: 'OPEN EVIDENCE' }
    if (selected.kind === 'claim') return { to: `/cases/${cid}/claims`, text: 'VIEW CLAIMS' }
    if (selected.kind === 'contradiction') return { to: `/cases/${cid}/contradictions`, text: 'VIEW CONTRADICTIONS' }
    if (selected.kind === 'law') return { to: `/cases/${cid}/legal`, text: 'VIEW LEGAL REFERENCES' }
    if (selected.kind === 'hearing') return { to: `/cases/${cid}/hearings`, text: 'VIEW HEARINGS' }
    return null
  }, [selected, cid])

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <button className="btn" onClick={() => { layout(); cy.current?.fit(undefined, 30) }}>[ RE-LAYOUT ]</button>
        <button className="btn" onClick={() => { setSelected(null); cy.current?.elements().removeClass('dim') }} disabled={!selected}>[ CLEAR FOCUS ]</button>
        <span className="lbl ml-auto">{info.n} NODES · {info.e} EDGES{busy ? ' · WORKING…' : ''}</span>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mb-2 text-[12px]">
        <span className="lbl">FILTER</span>
        {kinds.map((k) => (
          <label key={k} className="cursor-pointer"><input type="checkbox" checked={!hidden.has(k)}
            onChange={() => setHidden((h) => {
              const n = new Set(h)
              if (n.has(k)) n.delete(k); else n.add(k)
              return n
            })} /> {KIND_LABEL[k] || k.toUpperCase()}</label>
        ))}
      </div>
      {err && <div style={{ fontWeight: 700 }}>{err}</div>}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="relative border border-line" style={{ height: 'calc(100vh - 300px)', minHeight: 420 }}>
          <div ref={box} style={{ width: '100%', height: '100%' }} />
          {info.n === 0 && !busy && <div className="absolute inset-0 grid place-items-center text-mut">NO GRAPH YET. RUN ANALYSIS FIRST.</div>}
        </div>
        <aside className="border border-line p-3 min-h-[200px]">
          <div className="lbl border-b border-line pb-1 mb-2">NODE INSPECTOR</div>
          {!selected ? <div className="text-mut">Select a node to see what it represents and how it is connected. Edges show relationships, never proof.</div> : (
            <>
              <Field k="Type">{KIND_LABEL[selected.kind] || selected.kind}</Field>
              <Field k="Label">{selected.label}</Field>
              {selected.detail && <Field k="Details">{selected.detail}</Field>}
              {deepLink && <Link className="btn no-underline" to={deepLink.to}>[ {deepLink.text} ]</Link>}
            </>
          )}
        </aside>
      </div>
      <div className="lbl mt-2">A GRAPH EDGE IS A RELATIONSHIP BACKED BY THE CASE MODEL, NOT PROOF. DOUBLE-BORDERED NODES ARE POTENTIAL CONTRADICTIONS.</div>
    </div>
  )
}
