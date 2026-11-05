import { reactive } from 'vue';

export interface ConfirmOptions {
  title: string;
  message?: string;
  confirmText?: string;
  danger?: boolean;
}

export interface ConfirmState {
  open: boolean;
  title: string;
  message: string;
  confirmText: string;
  danger: boolean;
}

// 全站只有一个确认弹窗实例（ConfirmDialog 挂在 App.vue），这里保存它的状态与待决 promise。
export const confirmState = reactive<ConfirmState>({
  open: false,
  title: '',
  message: '',
  confirmText: '确认',
  danger: true,
});

let pending: ((ok: boolean) => void) | null = null;

/** 打开确认弹窗，用户选择后 resolve；用于替代 window.confirm。 */
export function useConfirm(): (options: ConfirmOptions) => Promise<boolean> {
  return (options) => {
    // 前一个还没答复就换内容时按取消处理，避免 promise 永远悬着。
    pending?.(false);
    confirmState.title = options.title;
    confirmState.message = options.message ?? '';
    confirmState.confirmText = options.confirmText ?? '确认';
    confirmState.danger = options.danger ?? true;
    confirmState.open = true;
    return new Promise<boolean>((resolve) => {
      pending = resolve;
    });
  };
}

export function settleConfirm(ok: boolean): void {
  confirmState.open = false;
  const resolve = pending;
  pending = null;
  resolve?.(ok);
}
