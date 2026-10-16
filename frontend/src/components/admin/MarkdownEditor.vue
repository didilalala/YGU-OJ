<script setup>
/**
 * 题面编辑器（md-editor-v3）。
 *
 * 只保留不依赖 CDN 的工具栏功能：去掉了 Mermaid、Prettier、全屏（screenfull）与 GitHub 链接，
 * 图片裁剪使用本地的 cropperjs；
 * 预览与前台一致（本地 KaTeX、DOMPurify 过滤）。
 * 系统没有图片存储，粘贴、拖入或上传的图片转为 data URI 内嵌在题面中，单张不超过 1MB。
 */
import { useId } from 'vue'
import { MdEditor, config } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import { ElMessage } from 'element-plus'

import { sanitizeHtml } from '@/utils/markdown'

// 图片按钮的「裁剪上传」默认从 unpkg 加载 cropperjs，改用本地版本（config 为深合并，不影响全局其余配置）
config({ editorExtensions: { cropper: { instance: Cropper } } })

const MAX_IMAGE_SIZE = 1024 * 1024

defineProps({
  height: { type: String, default: '320px' },
  placeholder: { type: String, default: '' },
  readOnly: { type: Boolean, default: false },
})
const model = defineModel({ type: String, default: '' })

const id = `md-editor-${useId()}`

const toolbars = [
  'bold',
  'italic',
  'strikeThrough',
  'title',
  'sub',
  'sup',
  'quote',
  'unorderedList',
  'orderedList',
  'codeRow',
  'code',
  'link',
  'image',
  'table',
  'katex',
  '-',
  'revoke',
  'next',
  '=',
  'pageFullscreen',
  'preview',
]

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function onUploadImg(files, callback) {
  const accepted = files.filter((file) => file.type.startsWith('image/') && file.size <= MAX_IMAGE_SIZE)
  if (accepted.length < files.length) ElMessage.warning('图片需小于 1MB，超出的已忽略')
  callback(await Promise.all(accepted.map(readAsDataUrl)))
}
</script>

<template>
  <MdEditor
    :id="id"
    v-model="model"
    :style="{ height }"
    :toolbars="toolbars"
    :footers="[]"
    :placeholder="placeholder"
    :read-only="readOnly"
    :sanitize="sanitizeHtml"
    :on-upload-img="onUploadImg"
    preview-theme="default"
    no-prettier
    no-highlight
    no-mermaid
    no-echarts
  />
</template>
