import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth'
import { AppShell } from './components/Shell'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import NewCase from './pages/NewCase'
import Notifications from './pages/Notifications'
import Search from './pages/Search'
import HearingRoom from './pages/HearingRoom'
import CaseLayout from './components/CaseLayout'
import Investigation from './pages/case/Investigation'
import ReviewTab from './pages/case/ReviewTab'
import CaseGraph from './pages/case/Graph'
import Parties from './pages/case/Parties'
import Statements from './pages/case/Statements'
import Evidence from './pages/case/Evidence'
import EvidenceDetail from './pages/case/EvidenceDetail'
import TimelineTab from './pages/case/TimelineTab'
import Claims from './pages/case/Claims'
import Contradictions from './pages/case/Contradictions'
import Legal from './pages/case/Legal'
import Hearings from './pages/case/Hearings'
import Decision from './pages/case/Decision'
import Audit from './pages/case/Audit'
import Report from './pages/case/Report'

function RequireAuth() {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-6 quiet blink">LOADING…</div>
  if (!user) return <Navigate to="/login" replace />
  return <AppShell><Outlet /></AppShell>
}

// Only five destinations exist: Cases, New Case, Investigation, Graph, Review & Resolution.
// The five features requested map to the case routes below; everything else is a section.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Navigate to="/cases" replace />} />
        <Route path="/cases" element={<Dashboard />} />
        <Route path="/cases/new" element={<NewCase />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/search" element={<Search />} />
        <Route path="/hearings/:id" element={<HearingRoom />} />
        <Route path="/cases/:caseId" element={<CaseLayout />}>
          <Route index element={<Investigation />} />
          <Route path="graph" element={<CaseGraph />} />
          <Route path="review" element={<ReviewTab />} />
          <Route path="parties" element={<Parties />} />
          <Route path="statements" element={<Statements />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="evidence/:evidenceId" element={<EvidenceDetail />} />
          <Route path="timeline" element={<TimelineTab />} />
          <Route path="claims" element={<Claims />} />
          <Route path="contradictions" element={<Contradictions />} />
          <Route path="legal" element={<Legal />} />
          <Route path="hearings" element={<Hearings />} />
          <Route path="decision" element={<Decision />} />
          <Route path="audit" element={<Audit />} />
          <Route path="report" element={<Report />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/cases" replace />} />
    </Routes>
  )
}
