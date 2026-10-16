import request from './request'

export const submissionApi = {
  submit: (data) => request.post('/submissions', data),
  // 轮询时不弹错误提示，由页面自行处理
  detail: (id, config) => request.get(`/submissions/${id}`, config),
  list: (params) => request.get('/submissions', { params }),
}
