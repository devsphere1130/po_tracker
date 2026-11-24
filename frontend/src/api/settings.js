import api, { resource } from './client'

export const usersApi = resource('auth/users')
export const getCompany = () => api.get('/auth/company/').then((r) => r.data)
export const saveCompany = (data) => api.patch('/auth/company/', data).then((r) => r.data)
export const auditApi = resource('auth/audit-logs')
