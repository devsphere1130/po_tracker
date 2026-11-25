import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../api/client'
import { fetchCached, peek } from '../api/cache'

/** Single resource: returns the cached copy for `key` immediately, then refreshes it from the server. */
export default function useCached(key, fetcher) {
  const [state, setState] = useState({ key, data: peek(key), error: '' })
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher
  const latest = useRef(key)
  latest.current = key

  const load = useCallback(() => fetchCached(key, () => fetcherRef.current()).then(
    (data) => { if (latest.current === key) setState({ key, data, error: '' }) },
    (e) => { if (latest.current === key) setState({ key, data: undefined, error: errorMessage(e) }) },
  ), [key])

  useEffect(() => { load() }, [load])

  const current = state.key === key ? state : { data: undefined, error: '' }
  const setData = (data) => setState({ key, data, error: '' })
  return { data: current.data ?? peek(key), error: current.error, reload: load, setData }
}
