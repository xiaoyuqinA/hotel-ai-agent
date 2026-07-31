"""Admin 测试配置 — 在导入 admin.app 前设置 mock 环境变量。"""

import os

# 设置特殊环境变量，让 app.py 中的 get_db 走 mock 路径
os.environ["ADMIN_TEST_MODE"] = "1"
