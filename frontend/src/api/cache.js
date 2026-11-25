// In-memory only (gone on browser refresh): pages show the last server response at once and refresh it quietly.
const data = new Map()
const pending = new Map()
const ids = new WeakMap()
let nextId = 0

export const peek = (key) => data.get(key)

/** Called after any change on the server, and on login/logout, so old figures are never shown. */
export function clearCache() {
  data.clear()
  pending.clear()
}

export function fetchCached(key, fetcher) {
  if (pending.has(key)) return pending.get(key)
  const request = fetcher().then(
    (res) => {
      if (pending.get(key) === request) { data.set(key, res); pending.delete(key) } // skipped if cleared meanwhile
      return res
    },
    (err) => {
      if (pending.get(key) === request) pending.delete(key)
      throw err
    },
  )
  pending.set(key, request)
  return request
}

/** Drops empty filters, as sent to the server. */
export const cleanParams = (params) => Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))

export function listKey(fetcher, params) {
  if (!ids.has(fetcher)) ids.set(fetcher, ++nextId)
  const clean = cleanParams(params)
  return JSON.stringify(['list', ids.get(fetcher), Object.keys(clean).sort().map((k) => [k, clean[k]])])
}
