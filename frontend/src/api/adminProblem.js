import request from './request'

function upload(url, file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  return request.post(url, form, {
    // 大文件上传不受默认 15 秒超时限制
    timeout: 0,
    onUploadProgress: (event) => onProgress?.(event.total ? Math.round((event.loaded / event.total) * 100) : 0),
  })
}

export const adminProblemApi = {
  list: (params) => request.get('/admin/problems', { params }),
  detail: (id, config) => request.get(`/admin/problems/${id}`, config),
  create: (data) => request.post('/admin/problems', data),
  update: (id, data) => request.patch(`/admin/problems/${id}`, data),
  remove: (id) => request.delete(`/admin/problems/${id}`),
  uploadTestCases: (file, onProgress) => upload('/admin/problems/test-cases', file, onProgress),
  importFps: (file, onProgress) => upload('/admin/problems/import-fps', file, onProgress),
}

export const adminKnowledgePointApi = {
  create: (data) => request.post('/admin/knowledge-points', data),
  update: (id, data) => request.patch(`/admin/knowledge-points/${id}`, data),
  remove: (id) => request.delete(`/admin/knowledge-points/${id}`),
}
