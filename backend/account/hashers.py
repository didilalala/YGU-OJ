from django.contrib.auth.hashers import PBKDF2PasswordHasher


class InitialPasswordHasher(PBKDF2PasswordHasher):
    """
    仅用于导入或重置时生成的初始密码（学号后六位）。

    默认的 PBKDF2 每次约 0.6 秒，一个 300 人的名单要哈希 3 分钟，超出请求时限。
    初始密码只有 10^6 种可能且可由学号推出，迭代次数再高也挡不住离线穷举，
    真正的保护是首次登录强制改密；因此这里用较少的迭代次数。
    学生首次登录成功时，Django 会自动用默认哈希器重新哈希（算法名不同即视为需要升级）。
    """

    algorithm = "pbkdf2_sha256_initial"
    iterations = 10000
