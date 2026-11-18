import api from './client'

export const getReport = (name, params) => api.get(`/reports/${name}/`, { params }).then((r) => r.data)
export const getPoReport = (kind, params) => api.get(`/reports/po-status/${kind}/`, { params }).then((r) => r.data)

/** CSV is fetched through axios (session cookie) and saved as a file. */
export async function downloadCsv(name, params) {
  const path = name.startsWith('po-status/') ? name : name
  const res = await api.get(`/reports/${path}/`, { params: { ...params, export: 'csv' }, responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `${name.replace('/', '-')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
