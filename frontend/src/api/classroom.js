import request from './request'

export const classroomApi = {
  mine: () => request.get('/classes/mine'),
}

export const adminClassApi = {
  list: (params) => request.get('/admin/classes', { params }),
  detail: (id, config) => request.get(`/admin/classes/${id}`, config),
  create: (data) => request.post('/admin/classes', data),
  update: (id, data) => request.patch(`/admin/classes/${id}`, data),
  remove: (id) => request.delete(`/admin/classes/${id}`),
  students: (id, params) => request.get(`/admin/classes/${id}/students`, { params }),
  addStudent: (id, data) => request.post(`/admin/classes/${id}/students`, data),
  importStudents: (id, file) => {
    const form = new FormData()
    form.append('file', file)
    return request.post(`/admin/classes/${id}/import`, form, { timeout: 0 })
  },
  removeStudents: (id, userIds) => request.post(`/admin/classes/${id}/remove-students`, { user_ids: userIds }),
  resetPasswords: (id, userIds) => request.post(`/admin/classes/${id}/reset-password`, { user_ids: userIds }),
  downloadTemplate: () => request.get('/admin/classes/import-template', { responseType: 'blob' }),
}
