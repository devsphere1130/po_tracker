import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../api/client'

/** Server-side paginated/filterable list. `fetcher(params)` must return a DRF page. */
export default function useList(fetcher, initial = {}) {
  const [params, setParams] = useState({ page: 1, page_size: 10, ...initial })
  const [data, setData] = useState({ results: [], count: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const seq = useRef(0)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const load = useCallback(async () => {
    const id = ++seq.current
    setLoading(true)
    setError('')
    try {
      const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
      const res = await fetcherRef.current(clean)
      if (id === seq.current) setData(res)
    } catch (e) {
      if (id === seq.current) setError(errorMessage(e))
    } finally {
      if (id === seq.current) setLoading(false)
    }
  }, [params])

  useEffect(() => { load() }, [load])

  const setFilter = (key, value) => setParams((p) => ({ ...p, [key]: value, page: 1 }))
  const setPage = (page) => setParams((p) => ({ ...p, page }))
  const setPageSize = (page_size) => setParams((p) => ({ ...p, page_size, page: 1 }))
  const reset = () => setParams({ page: 1, page_size: params.page_size, ...initial })

  return { params, data, rows: data.results || [], count: data.count || 0, loading, error, reload: load, setFilter, setPage, setPageSize, reset }
}
