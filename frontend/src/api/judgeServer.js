import request from './request'

export const judgeServerApi = {
  list: (config) => request.get('/admin/judge-servers', config),
  setEnabled: (id, isEnabled) => request.patch(`/admin/judge-servers/${id}`, { is_enabled: isEnabled }),
  remove: (id) => request.delete(`/admin/judge-servers/${id}`),
}
