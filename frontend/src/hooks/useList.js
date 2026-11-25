import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../api/client'
import { cleanParams, fetchCached, listKey, peek } from '../api/cache'

/** Server-side paginated/filterable list. `fetcher(params)` must return a DRF page. */
export default function useList(fetcher, initial = {}) {
  const [params, setParams] = useState({ page: 1, page_size: 10, ...initial })
  const [data, setData] = useState(() => peek(listKey(fetcher, params)) || { results: [], count: 0 })
  const [loading, setLoading] = useState(() => !peek(listKey(fetcher, params)))
  const [error, setError] = useState('')
  const seq = useRef(0)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const load = useCallback(async () => {
    const id = ++seq.current
    const key = listKey(fetcherRef.current, params)
    const cached = peek(key)
    if (cached) setData(cached)
    setLoading(!cached)
    setError('')
    try {
      const res = await fetchCached(key, () => fetcherRef.current(cleanParams(params)))
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
