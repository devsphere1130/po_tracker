import api, { resource } from './client'

const base = resource('ocr/extractions')
export const ocrApi = {
  list: base.list,
  get: base.get,
  saveDraft: (id, draft_data) => api.patch(`/ocr/extractions/${id}/`, { draft_data }).then((r) => r.data),
  upload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/ocr/extractions/upload/', fd).then((r) => r.data)
  },
  scan: (id) => api.post(`/ocr/extractions/${id}/scan/`).then((r) => r.data),
  verify: (id, form) => api.post(`/ocr/extractions/${id}/verify/`, form).then((r) => r.data),
  createPo: (id) => api.post(`/ocr/extractions/${id}/create-po/`).then((r) => r.data),
  engineStatus: () => api.get('/ocr/extractions/engine-status/').then((r) => r.data),
}
