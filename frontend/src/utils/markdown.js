/**
 * md-editor-v3 全局配置：所有依赖本地打包，机房断网时题面也能正常显示。
 *
 * - KaTeX 使用本地实例（默认会从 unpkg 加载）；
 * - 开启 markdown-it 的原生 HTML（FPS 导入的题面是 HTML），渲染结果统一经 DOMPurify 过滤脚本；
 * - 代码高亮、Mermaid、ECharts 的脚本或主题样式需要从 CDN 加载，题面中用不到，在组件上关闭。
 */
import { config } from 'md-editor-v3'
import katex from 'katex'
import DOMPurify from 'dompurify'
import 'katex/dist/katex.min.css'
import 'md-editor-v3/lib/preview.css'

config({
  editorExtensions: {
    katex: { instance: katex },
  },
  markdownItConfig(md) {
    md.set({ html: true })
  },
})

export function sanitizeHtml(html) {
  return DOMPurify.sanitize(html)
}
