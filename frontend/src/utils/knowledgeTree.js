/**
 * 把平铺的知识点列表（含 parent）组装成 el-tree / el-tree-select 需要的树。
 * 上级不在列表中（如按课程筛选后）的节点作为根节点。
 */
export function buildKnowledgeTree(points) {
  const nodes = new Map(points.map((p) => [p.id, { ...p, value: p.id, label: p.name, children: [] }]))
  const roots = []
  for (const point of points) {
    const node = nodes.get(point.id)
    const parent = point.parent && nodes.get(point.parent)
    ;(parent ? parent.children : roots).push(node)
  }
  return roots
}

export function courseNames(points) {
  return [...new Set(points.map((p) => p.course).filter(Boolean))].sort()
}
