import { useCase } from '../../components/CaseLayout'
import Hearings from './Hearings'
import Review from './Review'
import Decision from './Decision'
import Audit from './Audit'
import Report from './Report'

const SECTIONS = [['hearings', 'Hearings'], ['decision', 'Decision management'], ['closure', 'Case closure']]

export default function ReviewTab() {
  const { caseData } = useCase()
  return (
    <div className="max-w-[1150px]">
      <div className="mb-3">
        <div className="lbl">Review &amp; resolution</div>
        <p className="text-[15px]" style={{ fontWeight: 700 }}>Hearings, decision and closure for {caseData.id}.</p>
      </div>
      <nav className="flex flex-wrap gap-1 mb-4" aria-label="review sections">
        {SECTIONS.map(([id, label]) => <a key={id} href={`#${id}`} className="nav-sub">{label}</a>)}
      </nav>

      <section id="hearings" className="scroll-mt-2">
        <Hearings />
      </section>

      <section id="decision" className="scroll-mt-2 mt-8">
        <h2 className="text-[14px] tracking-[.14em] uppercase border-b border-line pb-1 mb-3">Decision management</h2>
        <Review />
        <div className="mt-6"><Decision /></div>
      </section>

      <section id="closure" className="scroll-mt-2 mt-8">
        <h2 className="text-[14px] tracking-[.14em] uppercase border-b border-line pb-1 mb-3">Case closure</h2>
        <Audit />
        <div className="mt-6"><Report /></div>
      </section>
    </div>
  )
}
