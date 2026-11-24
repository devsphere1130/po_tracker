import api, { resource } from './client'

export const purchaseOrdersApi = {
  ...resource('purchase-orders'),
  cancel: (id, reason) => api.post(`/purchase-orders/${id}/cancel/`, { reason }).then((r) => r.data),
  reopen: (id) => api.post(`/purchase-orders/${id}/reopen/`).then((r) => r.data),
  uploadAttachment: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/purchase-orders/${id}/attachment/`, fd).then((r) => r.data)
  },
}
