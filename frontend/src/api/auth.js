import request from './request'

export const authApi = {
  login: (data) => request.post('/auth/login', data),
  me: (config) => request.get('/auth/me', config),
  changePassword: (data) => request.post('/auth/change-password', data),
  register: (data) => request.post('/auth/register', data),
  bindStudent: (data) => request.post('/auth/bind-student', data),
  profile: (config) => request.get('/profile', config),
  site: (config) => request.get('/site', config),
}
