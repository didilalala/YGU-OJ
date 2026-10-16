import request from './request'

export const examApi = {
  mine: () => request.get('/exams'),
  // 公开竞赛列表，访客也可浏览
  contests: () => request.get('/contests'),
  active: (config) => request.get('/exams/active', config),
  detail: (id, config) => request.get(`/exams/${id}`, config),
  join: (id, password) => request.post(`/exams/${id}/join`, { password }),
  finish: (id) => request.post(`/exams/${id}/finish`),
  rank: (id, config) => request.get(`/exams/${id}/rank`, config),
}

export const adminExamApi = {
  list: (params) => request.get('/admin/exams', { params }),
  detail: (id, config) => request.get(`/admin/exams/${id}`, config),
  create: (data) => request.post('/admin/exams', data),
  update: (id, data) => request.patch(`/admin/exams/${id}`, data),
  remove: (id) => request.delete(`/admin/exams/${id}`),
  monitor: (id, config) => request.get(`/admin/exams/${id}/monitor`, config),
  reopen: (id, userId) => request.post(`/admin/exams/${id}/participants/${userId}/reopen`),
}
