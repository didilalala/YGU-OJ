import request from './request'

export const assignmentApi = {
  // status: todo | not_started | ended
  mine: (params) => request.get('/assignments', { params }),
  detail: (id, config) => request.get(`/assignments/${id}`, config),
}

export const adminAssignmentApi = {
  list: (params) => request.get('/admin/assignments', { params }),
  detail: (id, config) => request.get(`/admin/assignments/${id}`, config),
  create: (data) => request.post('/admin/assignments', data),
  update: (id, data) => request.patch(`/admin/assignments/${id}`, data),
  remove: (id) => request.delete(`/admin/assignments/${id}`),
  results: (id, config) => request.get(`/admin/assignments/${id}/results`, config),
}
