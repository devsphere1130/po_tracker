import api, { resource } from './client'

export const inboxApi = {
  ...resource('inbox/messages'),
  sync: (provider = 'auto') => api.post('/inbox/messages/sync/', { provider }).then((r) => r.data),
  simulate: () => api.post('/inbox/messages/simulate/').then((r) => r.data),
  scan: (id) => api.post(`/inbox/messages/${id}/scan/`).then((r) => r.data),
  mark: (id, status, note = '') => api.post(`/inbox/messages/${id}/mark/`, { status, note }).then((r) => r.data),
  connections: () => api.get('/inbox/connections/').then((r) => r.data),
  updateConnection: (id, data) => api.patch(`/inbox/connections/${id}/`, data).then((r) => r.data),
  connect: (id) => api.post(`/inbox/connections/${id}/connect/`).then((r) => r.data),
  disconnect: (id) => api.post(`/inbox/connections/${id}/disconnect/`).then((r) => r.data),
}
