import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmt } from '../lib/api'
import { Empty, ErrorBanner, Loading, Section } from '../components/ui'
import type { J } from '../types'

export default function Notifications() {
  const [data, setData] = useState<J>(null)
  const [err, setErr] = useState('')
  const load = useCallback(() => {
    api.get('/notifications').then(setData).catch((e) => setErr((e as Error).message))
  }, [])
  useEffect(() => { load() }, [load])

  async function readOne(id: number) { await api.post(`/notifications/${id}/read`); load() }
  async function readAll() { await api.post('/notifications/read-all'); load() }

  return (
    <div className="max-w-[820px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title={`Notifications${data ? ` · ${data.unread} unread` : ''}`} right={<button className="btn" onClick={readAll}>[ MARK ALL READ ]</button>}>
        {!data ? <Loading /> : data.items.length === 0 ? <Empty>No notifications.</Empty> : (
          <div className="grid gap-2">
            {data.items.map((n: J) => (
              <div key={n.id} className="border p-2" style={{ borderStyle: n.read ? 'solid' : 'dashed', borderColor: 'var(--line)' }}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="lbl">{n.kind.replaceAll('_', ' ')}</span>
                  <span className="lbl ml-auto">{fmt.time(n.created_at)}</span>
                </div>
                <div style={{ fontWeight: n.read ? 400 : 700 }}>{n.title}</div>
                {n.body && <div className="text-[12px]">{n.body}</div>}
                <div className="flex gap-2 mt-1">
                  {n.case_id && <Link className="link" to={`/cases/${n.case_id}`}>{n.case_id}</Link>}
                  {!n.read && <button className="btn" onClick={() => readOne(n.id)}>[ MARK READ ]</button>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}
