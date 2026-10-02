import { useState } from 'react'
import Journey from './Journey'
import EventList from './Timeline'

// One timeline, two readings: the interactive case journey map (default) and the dense
// evidence-event list. Both render from the same underlying case data.
export default function TimelineTab() {
  const [mode, setMode] = useState<'map' | 'list'>('map')
  return (
    <div>
      <div className="flex gap-1 mb-3" role="group" aria-label="timeline view">
        <button className={'btn ' + (mode === 'map' ? 'on' : '')} onClick={() => setMode('map')}>[ JOURNEY MAP ]</button>
        <button className={'btn ' + (mode === 'list' ? 'on' : '')} onClick={() => setMode('list')}>[ EVENT LIST ]</button>
      </div>
      {mode === 'map' ? <Journey /> : <EventList />}
    </div>
  )
}
