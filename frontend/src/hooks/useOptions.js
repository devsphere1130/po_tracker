import { useEffect, useState } from 'react'
import { customersApi } from '../api/customers'
import { materialsApi } from '../api/materials'

/** Loads every active (or all) customer/material for dropdowns. */
function useAll(api, activeOnly) {
  const [items, setItems] = useState([])
  const [version, setVersion] = useState(0)
  useEffect(() => {
    let live = true
    api.list({ page_size: 200, ordering: 'name', ...(activeOnly ? { is_active: true } : {}) }).then((r) => live && setItems(r.results)).catch(() => {})
    return () => { live = false }
  }, [api, activeOnly, version])
  return [items, () => setVersion((v) => v + 1)]
}

export const useCustomers = (activeOnly = false) => useAll(customersApi, activeOnly)
export const useMaterials = (activeOnly = false) => useAll(materialsApi, activeOnly)
