import type { ReactNode } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth'
import { MobileNav, Sidebar, StatusBar, TopBar } from './components/Shell'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Cases from './pages/Cases'
import Uploads from './pages/Uploads'
import CaseLayout from './components/CaseLayout'
import CaseOverview from './pages/case/Overview'
import Parties from './pages/case/Parties'
import Statements from './pages/case/Statements'
import Evidence from './pages/case/Evidence'
import EvidenceDetail from './pages/case/EvidenceDetail'
import CaseTimeline from './pages/case/TimelineTab'
import CaseClaims from './pages/case/Claims'
import CaseContradictions from './pages/case/Contradictions'
import CaseGraph from './pages/case/Graph'
import CaseLegal from './pages/case/Legal'
import CaseReview from './pages/case/Review'
import CaseDecision from './pages/case/Decision'
import CaseHearings from './pages/case/Hearings'
import CaseAudit from './pages/case/Audit'
import CaseReport from './pages/case/Report'
import HearingRoom from './pages/HearingRoom'
import Notifications from './pages/Notifications'
import Search from './pages/Search'

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="grid h-screen w-screen overflow-hidden" style={{ gridTemplateRows: 'auto auto 1fr auto' }}>
      <TopBar />
      <MobileNav />
      <div className="grid min-h-0 grid-cols-1 lg:grid-cols-[200px_minmax(0,1fr)]">
        <Sidebar />
        <main className="overflow-auto p-4 min-w-0">{children}</main>
      </div>
      <StatusBar />
    </div>
  )
}

function RequireAuth() {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-6 text-mut blink">LOADING…</div>
  if (!user) return <Navigate to="/login" replace />
  return <Shell><Outlet /></Shell>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/uploads" element={<Uploads />} />
        <Route path="/cases/new" element={<Navigate to="/uploads" replace />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/search" element={<Search />} />
        <Route path="/hearings/:id" element={<HearingRoom />} />
        <Route path="/cases/:caseId" element={<CaseLayout />}>
          <Route index element={<CaseOverview />} />
          <Route path="parties" element={<Parties />} />
          <Route path="statements" element={<Statements />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="evidence/:evidenceId" element={<EvidenceDetail />} />
          <Route path="timeline" element={<CaseTimeline />} />
          <Route path="claims" element={<CaseClaims />} />
          <Route path="contradictions" element={<CaseContradictions />} />
          <Route path="legal" element={<CaseLegal />} />
          <Route path="graph" element={<CaseGraph />} />
          <Route path="hearings" element={<CaseHearings />} />
          <Route path="review" element={<CaseReview />} />
          <Route path="decision" element={<CaseDecision />} />
          <Route path="audit" element={<CaseAudit />} />
          <Route path="report" element={<CaseReport />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
