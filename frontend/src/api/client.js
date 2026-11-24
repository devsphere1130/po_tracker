import axios from 'axios'

// Same-origin through the Vite proxy: session cookie + CSRF header (X-CSRFToken from the csrftoken cookie).
const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  paramsSerializer: { indexes: null }, // status=a&status=b (Django multiple-choice filters)
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const code = err.response?.data?.error?.code
    if (code === 'not_authenticated' && !err.config.url.includes('/auth/me')) {
      window.dispatchEvent(new Event('auth:expired'))
    }
    return Promise.reject(err)
  },
)

function flatten(details, prefix = '') {
  if (!details) return []
  if (typeof details === 'string') return [prefix ? `${prefix}: ${details}` : details]
  if (Array.isArray(details)) return details.flatMap((d) => flatten(d, prefix))
  return Object.entries(details).flatMap(([k, v]) => flatten(v, k === 'non_field_errors' ? prefix : k))
}

/** Human-readable message from the consistent API error envelope. */
export function errorMessage(err) {
  const e = err.response?.data?.error
  if (!e) return err.response ? `Request failed (${err.response.status}).` : 'Cannot reach the server. Is the backend running?'
  const lines = flatten(e.details)
  return lines.length ? `${e.message} ${lines.join(' · ')}` : e.message
}

/** Field → message map for inline form errors (top-level fields only). */
export function fieldErrors(err) {
  const d = err.response?.data?.error?.details
  if (!d || typeof d !== 'object' || Array.isArray(d)) return {}
  return Object.fromEntries(Object.entries(d).map(([k, v]) => [k, flatten(v).join(' ')]))
}

export default api

/** Generic REST resource helper to keep per-module service files tiny. */
export function resource(path) {
  return {
    list: (params) => api.get(`/${path}/`, { params }).then((r) => r.data),
    get: (id) => api.get(`/${path}/${id}/`).then((r) => r.data),
    create: (data) => api.post(`/${path}/`, data).then((r) => r.data),
    update: (id, data) => api.patch(`/${path}/${id}/`, data).then((r) => r.data),
    remove: (id) => api.delete(`/${path}/${id}/`),
  }
}
