/**
 * 复制文本。校园网常以 http + IP 部署，此时浏览器不提供 navigator.clipboard（仅限安全上下文），
 * 退回到 execCommand 方式。
 */
export async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  try {
    if (!document.execCommand('copy')) throw new Error('复制失败')
  } finally {
    document.body.removeChild(textarea)
  }
}
