import request from './request'

export const adminSettingsApi = {
  list: (config) => request.get('/admin/settings', config),
  update: (changes) => request.patch('/admin/settings', changes),
}

export const adminLanguageApi = {
  list: (config) => request.get('/admin/languages', config),
  create: (data) => request.post('/admin/languages', data),
  update: (id, data) => request.patch(`/admin/languages/${id}`, data),
}
