import request from './request'

export const statsApi = {
  mine: () => request.get('/scores/mine'),
  classOverview: (id, config) => request.get(`/admin/stats/classes/${id}`, config),
  assignment: (id, config) => request.get(`/admin/stats/assignments/${id}`, config),
  exam: (id, config) => request.get(`/admin/stats/exams/${id}`, config),
  classKnowledge: (id, config) => request.get(`/admin/stats/classes/${id}/knowledge`, config),
  exportClass: (id) => request.get(`/admin/stats/classes/${id}/export`, { responseType: 'blob', timeout: 0 }),
}
