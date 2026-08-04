/**
 * 中文文案字典
 * key 与 en.ts 一一对应，缺失时 t() 回退到这里。
 */
export default {
  // 通用
  'app.title': '酒店评论AI助手',
  'app.subtitle': '智能生成 OTA 评论回复',

  // 语言
  'lang.switch': 'English',

  // ── 邀请码视图 ──
  'invite.label': '🔑 邀请码',
  'invite.hint': '请输入商家邀请码开始使用',
  'invite.placeholder': 'INVITE-XXXX',
  'invite.verify': '验证',
  'invite.verifying': '验证中...',
  'invite.required': '请输入邀请码',
  'invite.invalid': '邀请码无效',
  'invite.not_exist': '邀请码不存在',
  'invite.expired': '邀请码已过期',
  'invite.validate_failed': '验证失败',
  'invite.conn_failed': '无法连接服务器',
  'invite.verify_failed_retry': '验证失败，请稍后重试',
  'invite.unset': '未设置邀请码',
  'invite.not_set': '未设置',
  'invite.change': '更换',
  'invite.edit_title': '修改邀请码',
  'invite.new_placeholder': '输入新邀请码',
  'invite.cancel': '取消',
  'invite.save': '保存',
  'invite.updated': '✅ 邀请码已更新',

  // ── 创建酒店视图 ──
  'create.welcome': '欢迎使用',
  'create.hint': '请先创建酒店配置，开始使用 AI 回复助手',
  'create.name_placeholder': '酒店名称（如：深圳湾万豪酒店）',
  'create.city_placeholder': '所在城市（如：深圳）',
  'create.submit': '创建酒店',
  'create.skip': '跳过',
  'create.creating': '创建中...',
  'create.name_required': '请输入酒店名称',
  'create.city_required': '请输入所在城市',
  'create.failed': '创建失败：',

  // ── 酒店首页 ──
  'home.reply_config': '回复配置',
  'home.loading': '加载中...',
  'home.edit_settings': '✎ 编辑回复设置',
  'home.tone': '回复语气',
  'home.style': '回复风格',
  'home.rules': '回复规则',
  'home.unset': '未设置',
  'home.none': '无',

  // ── 编辑设置 ──
  'edit.back': '← 返回',
  'edit.tone_placeholder': '例如：专业、温暖、真诚',
  'edit.style_placeholder': '例如：正式但具有人情味',
  'edit.rules_label': '回复规则（每行一条）',
  'edit.rules_placeholder': '投诉必须先表达歉意',
  'edit.cancel': '取消',
  'edit.save': '保存设置',
  'edit.saving': '保存中...',
  'edit.tone_required': '回复语气不能为空',
  'edit.saved': '✅ 设置已保存',
  'edit.save_failed': '保存失败：',
  'edit.load_failed': '加载失败：',

  // ── 酒店列表弹窗 ──
  'modal.select_hotel': '选择酒店',
  'modal.new_hotel': '+ 创建新酒店',

  // ── 状态 ──
  'status.load_failed': '加载失败：',

  // ── 悬浮面板 (content-script) ──
  'widget.title': 'AI 回复助手',
  'widget.minimize': '最小化',
  'widget.close': '关闭',
  'widget.no_hotel': '请先在扩展中创建或选择酒店',
  'widget.no_hotel_hint': '点击 Chrome 工具栏的扩展图标打开配置',
  'widget.review_placeholder': '选中评论后，点击「生成回复」',
  'widget.generate': 'AI生成回复',
  'widget.generating': '正在生成回复...',
  'widget.waiting': '等待回复...',
  'widget.reply_generated': '回复已生成',
  'widget.review_label': '评论：',
  'widget.empty_reply': '（空回复）',
  'widget.edit_reply': '✎ 编辑回复',
  'widget.copy': '📋 复制',
  'widget.regenerate': '重新生成',
  'widget.unknown_error': '未知错误',
  'widget.operation_failed': '操作失败',
  'widget.retry': '重试',
  'widget.editing_reply': '编辑回复',
  'widget.edit_cancel': '取消',
  'widget.edit_confirm': '确认',
  'widget.edit_publish': '确认并发布',
  'widget.page_not_supported': '当前页面不支持',
  'widget.no_review': '无法获取评论内容',
  'widget.set_invite_first': '请先在扩展中设置邀请码',
  'widget.ext_refreshed': '扩展已刷新，请重试',
  'widget.conn_error': '扩展连接异常，请刷新页面后重试',
  'widget.copied': '✅ 已复制到剪贴板',
  'widget.processing': '处理中',

  // ── 后端状态文案（display_name 本地化）──
  'status.workflow_started': '工作流开始',
  'status.workflow_completed': '工作流完成',
  'status.workflow_failed': '工作流失败',
  'status.workflow_cancelled': '工作流取消',
  'status.analysis_started': '分析开始',
  'status.analysis_completed': '分析完成',
  'status.analysis_failed': '分析失败',
  'status.generation_started': '生成开始',
  'status.generation_completed': '生成完成',
  'status.generation_failed': '生成失败',
  'status.review_started': '审核开始',
  'status.review_completed': '审核完成',
  'status.review_failed': '审核失败',
} as const;
