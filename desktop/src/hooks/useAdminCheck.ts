import { useState, useEffect } from 'react'
import { api } from '../lib/api'

export function useAdminCheck() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api.isAdmin()
      .then(r => { if (!cancelled) setIsAdmin(r.is_admin) })
      .catch(() => { if (!cancelled) setIsAdmin(false) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  return { isAdmin, loading }
}
