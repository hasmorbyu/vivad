import { useEffect, useState } from 'react'

// One data model, two renderings: hooks report the viewport so the journey can lay itself
// out horizontally or vertically without duplicating any timeline logic.
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false)
  useEffect(() => {
    const m = window.matchMedia(query)
    const update = () => setMatches(m.matches)
    update()
    m.addEventListener('change', update)
    return () => m.removeEventListener('change', update)
  }, [query])
  return matches
}
