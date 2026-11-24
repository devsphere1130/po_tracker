import api from './client'

export const getCsrf = () => api.get('/auth/csrf/')
export const login = (username, password) => api.post('/auth/login/', { username, password }).then((r) => r.data)
export const logout = () => api.post('/auth/logout/')
export const me = () => api.get('/auth/me/').then((r) => r.data)
