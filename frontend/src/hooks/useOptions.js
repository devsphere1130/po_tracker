import { useEffect, useState } from 'react'
import { customersApi } from '../api/customers'
import { materialsApi } from '../api/materials'
import { fetchCached, listKey, peek } from '../api/cache'

/** Loads every active (or all) customer/material for dropdowns. */
function useAll(api, activeOnly) {
  const params = { page_size: 200, ordering: 'name', ...(activeOnly ? { is_active: true } : {}) }
  const key = listKey(api.list, params)
  const [items, setItems] = useState(() => peek(key)?.results || [])
  const [version, setVersion] = useState(0)
  useEffect(() => {
    let live = true
    fetchCached(key, () => api.list(params)).then((r) => live && setItems(r.results)).catch(() => {})
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, version])
  return [items, () => setVersion((v) => v + 1)]
}

export const useCustomers = (activeOnly = false) => useAll(customersApi, activeOnly)
export const useMaterials = (activeOnly = false) => useAll(materialsApi, activeOnly)
