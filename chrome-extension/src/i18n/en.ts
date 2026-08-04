/**
 * 英文文案字典
 */
export default {
  // 通用
  'app.title': 'Hotel Review AI Assistant',
  'app.subtitle': 'AI-generated OTA review replies',

  // 语言
  'lang.switch': '中文',

  // ── 邀请码视图 ──
  'invite.label': '🔑 Invite Code',
  'invite.hint': 'Enter your merchant invite code to get started',
  'invite.placeholder': 'INVITE-XXXX',
  'invite.verify': 'Verify',
  'invite.verifying': 'Verifying...',
  'invite.required': 'Please enter an invite code',
  'invite.invalid': 'Invalid invite code',
  'invite.not_exist': 'Invite code does not exist',
  'invite.expired': 'Invite code has expired',
  'invite.validate_failed': 'Validation failed',
  'invite.conn_failed': 'Unable to connect to server',
  'invite.verify_failed_retry': 'Verification failed, please try again later',
  'invite.unset': 'No invite code set',
  'invite.not_set': 'Not set',
  'invite.change': 'Change',
  'invite.edit_title': 'Change Invite Code',
  'invite.new_placeholder': 'Enter a new invite code',
  'invite.cancel': 'Cancel',
  'invite.save': 'Save',
  'invite.updated': '✅ Invite code updated',

  // ── 创建酒店视图 ──
  'create.welcome': 'Welcome',
  'create.hint': 'Create a hotel configuration to start using the AI reply assistant',
  'create.name_placeholder': 'Hotel name (e.g. Shenzhen Bay Marriott)',
  'create.city_placeholder': 'City (e.g. Shenzhen)',
  'create.submit': 'Create Hotel',
  'create.creating': 'Creating...',
  'create.name_required': 'Please enter a hotel name',
  'create.city_required': 'Please enter a city',
  'create.failed': 'Create failed: ',

  // ── 酒店首页 ──
  'home.reply_config': 'Reply Settings',
  'home.loading': 'Loading...',
  'home.edit_settings': '✎ Edit Reply Settings',
  'home.tone': 'Tone',
  'home.style': 'Style',
  'home.rules': 'Rules',
  'home.unset': 'Not set',
  'home.none': 'None',

  // ── 编辑设置 ──
  'edit.back': '← Back',
  'edit.tone_placeholder': 'e.g. Professional, warm, sincere',
  'edit.style_placeholder': 'e.g. Formal but personable',
  'edit.rules_label': 'Reply rules (one per line)',
  'edit.rules_placeholder': 'Always apologize first for complaints',
  'edit.cancel': 'Cancel',
  'edit.save': 'Save Settings',
  'edit.saving': 'Saving...',
  'edit.tone_required': 'Tone cannot be empty',
  'edit.saved': '✅ Settings saved',
  'edit.save_failed': 'Save failed: ',
  'edit.load_failed': 'Load failed: ',

  // ── 酒店列表弹窗 ──
  'modal.select_hotel': 'Select Hotel',
  'modal.new_hotel': '+ Create New Hotel',

  // ── 状态 ──
  'status.load_failed': 'Load failed: ',

  // ── 悬浮面板 (content-script) ──
  'widget.title': 'AI Reply Assistant',
  'widget.minimize': 'Minimize',
  'widget.close': 'Close',
  'widget.no_hotel': 'Please create or select a hotel in the extension first',
  'widget.no_hotel_hint': 'Click the extension icon in the Chrome toolbar to open settings',
  'widget.review_placeholder': 'Select a review, then click "Generate Reply"',
  'widget.generate': 'AI Generate Reply',
  'widget.generating': 'Generating reply...',
  'widget.waiting': 'Waiting for reply...',
  'widget.reply_generated': 'Reply generated',
  'widget.review_label': 'Review: ',
  'widget.empty_reply': '(Empty reply)',
  'widget.edit_reply': '✎ Edit Reply',
  'widget.copy': '📋 Copy',
  'widget.regenerate': 'Regenerate',
  'widget.unknown_error': 'Unknown error',
  'widget.operation_failed': 'Operation failed',
  'widget.retry': 'Retry',
  'widget.editing_reply': 'Edit Reply',
  'widget.edit_cancel': 'Cancel',
  'widget.edit_confirm': 'Confirm',
  'widget.edit_publish': 'Confirm & Publish',
  'widget.page_not_supported': 'This page is not supported',
  'widget.no_review': 'Unable to get review content',
  'widget.set_invite_first': 'Please set an invite code in the extension first',
  'widget.ext_refreshed': 'Extension was refreshed, please try again',
  'widget.conn_error': 'Extension connection error, please refresh the page and retry',
  'widget.copied': '✅ Copied to clipboard',
  'widget.processing': 'Processing',
} as const;
