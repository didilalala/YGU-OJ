// 与后端 account.models.User.Role 保持一致
export const ROLES = Object.freeze({
  REGULAR: 'regular',
  STUDENT: 'student',
  TEACHER: 'teacher',
  ADMIN: 'admin',
})

export const ROLE_LABELS = {
  [ROLES.REGULAR]: '普通用户',
  [ROLES.STUDENT]: '在校学生',
  [ROLES.TEACHER]: '教师',
  [ROLES.ADMIN]: '管理员',
}

// 可进入管理后台的角色
export const STAFF_ROLES = [ROLES.TEACHER, ROLES.ADMIN]
