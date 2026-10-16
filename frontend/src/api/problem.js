import request from './request'

export const problemApi = {
  list: (params) => request.get('/problems', { params }),
  detail: (id, config) => request.get(`/problems/${id}`, config),
  knowledgePoints: (params) => request.get('/knowledge-points', { params }),
}
