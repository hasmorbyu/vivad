import type { J } from '../types'

export class ApiError extends Error {}

const TOKEN_KEY = 'vivad-token'

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* storage unavailable */ }
}

// Error responses from the API are already plain-language; never surface a raw stack trace.
const MESSAGES: Record<number, string> = {
  401: 'Your session has expired. Please sign in again.',
  403: 'You do not have permission to perform this action.',
  404: 'The requested item could not be found.',
  409: 'That change conflicts with the current state. Refresh and try again.',
  413: 'The file is larger than the allowed limit.',
  415: 'That file type is not supported.',
  422: 'Some of the information provided was not valid.',
  500: 'Something went wrong on the server. The action was not applied.',
}

function friendly(status: number, detail: unknown, statusText: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  return MESSAGES[status] || statusText || 'The request could not be completed.'
}

async function req(path: string, init: RequestInit = {}): Promise<J> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let r: Response
  try {
    r = await fetch('/api' + path, { ...init, headers })
  } catch {
    throw new ApiError('The VIVAD service is unreachable. Check that the API is running.')
  }
  if (r.status === 401 && path !== '/auth/login') {
    setToken(null)
    window.dispatchEvent(new Event('vivad:unauthorized'))
  }
  if (!r.ok) {
    let detail: unknown = null
    try { detail = (await r.json()).detail } catch { /* not json */ }
    throw new ApiError(friendly(r.status, detail, r.statusText))
  }
  const ct = r.headers.get('content-type') || ''
  return ct.includes('application/json') ? r.json() : r.blob()
}

export const api = {
  get: (p: string) => req(p),
  post: (p: string, body?: J) => req(p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined }),
  patch: (p: string, body?: J) => req(p, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined }),
  del: (p: string) => req(p, { method: 'DELETE' }),
  upload(caseId: string, file: File, extra: Record<string, string>, onProgress: (pct: number) => void): Promise<J> {
    return new Promise((resolve, reject) => {
      const x = new XMLHttpRequest()
      x.open('POST', `/api/cases/${caseId}/evidence`)
      const token = getToken()
      if (token) x.setRequestHeader('Authorization', `Bearer ${token}`)
      x.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100))
      x.onload = () => {
        let j: J = {}
        try { j = JSON.parse(x.responseText) } catch { /* non-json */ }
        if (x.status < 300) resolve(j)
        else reject(new ApiError(friendly(x.status, j.detail, `HTTP ${x.status}`)))
      }
      x.onerror = () => reject(new ApiError('Upload failed: the service is unreachable.'))
      const fd = new FormData()
      fd.append('file', file)
      Object.entries(extra).forEach(([k, v]) => fd.append(k, v))
      x.send(fd)
    })
  },
  download: async (path: string): Promise<Blob> => (await req(path)) as Blob,
}

export const fmt = {
  n: (v: number | undefined) => (v ?? 0).toLocaleString('en-IN'),
  mb: (b: number) => (b / 1048576).toFixed(1) + ' MB',
  size: (b: number) => (b > 1048576 ? (b / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB'),
  hash: (h?: string) => (h ? h.slice(0, 6) + '…' + h.slice(-4) : ''),
  time: (t?: string | null) => (!t ? '--' : t.length === 10 ? t + ' --:--' : t.replace('T', ' ').slice(0, 19)),
  clock: (t?: string | null) => (!t || t.length === 10 ? '--:--' : t.slice(11, 16)),
  date: (t?: string | null) => {
    if (!t) return 'UNDATED'
    const d = new Date(t.slice(0, 10) + 'T00:00:00')
    return isNaN(d.getTime()) ? 'UNDATED' : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase()
  },
  money: (amount: number, currency = 'INR') => `${currency === 'INR' ? '₹' : currency + ' '}${(amount ?? 0).toLocaleString('en-IN')}`,
  label: (s?: string) => (s ? s.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()) : ''),
}
