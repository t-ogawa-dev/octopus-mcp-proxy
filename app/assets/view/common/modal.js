/**
 * 共通モーダルユーティリティ
 * confirm/alertダイアログをオリジナルモーダルで実装
 */

class CommonModal {
    constructor() {
        this.createModalElement();
    }

    createModalElement() {
        if (document.getElementById('commonModal')) {
            return;
        }

        const modalHTML = `
            <div class="modal fade" id="commonModal" tabindex="-1" aria-labelledby="commonModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="commonModalLabel"></h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="commonModalBody"></div>
                        <div class="modal-footer" id="commonModalFooter">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="commonModalCancel"></button>
                            <button type="button" class="btn btn-primary" id="commonModalConfirm"></button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const div = document.createElement('div');
        div.innerHTML = modalHTML;
        document.body.appendChild(div.firstElementChild);
        
        // Bootstrapモーダルを初期化（backdrop無効化）
        this.modal = new bootstrap.Modal(document.getElementById('commonModal'), {
            backdrop: false,  // backdropを無効化（カスタムモーダルと競合するため）
            keyboard: true    // ESCキーで閉じる機能は有効
        });
        this.modalElement = document.getElementById('commonModal');
    }

    /**
     * 確認ダイアログを表示
     * @param {string} message - 表示するメッセージ
     * @param {string} title - モーダルのタイトル（デフォルト: '確認'）
     * @param {Object} options - オプション
     * @param {string} options.confirmText - 確認ボタンのテキスト（デフォルト: 'OK'）
     * @param {string} options.cancelText - キャンセルボタンのテキスト（デフォルト: 'キャンセル'）
     * @param {string} options.confirmClass - 確認ボタンのクラス（デフォルト: 'btn-primary'）
     * @returns {Promise<boolean>} - ユーザーが確認ボタンをクリックした場合true
     */
    confirm(message, title = null, options = {}) {
        return new Promise((resolve) => {
            const {
                confirmText = 'OK',
                cancelText = t('common_cancel') || 'キャンセル',
                confirmClass = 'btn-primary'
            } = options;

            const defaultTitle = t('common_confirm') || '確認';
            document.getElementById('commonModalLabel').textContent = title || defaultTitle;
            document.getElementById('commonModalBody').textContent = message;
            
            const confirmBtn = document.getElementById('commonModalConfirm');
            const cancelBtn = document.getElementById('commonModalCancel');
            
            confirmBtn.textContent = confirmText;
            cancelBtn.textContent = cancelText;
            
            // ボタンのクラスをリセット
            confirmBtn.className = `btn ${confirmClass}`;
            
            // イベントリスナーをクリア
            const newConfirmBtn = confirmBtn.cloneNode(true);
            const newCancelBtn = cancelBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
            cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
            
            // 新しいイベントリスナーを追加
            newConfirmBtn.addEventListener('click', () => {
                this.modal.hide();
                resolve(true);
            });
            
            newCancelBtn.addEventListener('click', () => {
                this.modal.hide();
                resolve(false);
            });
            
            // モーダル外クリック・ESCキーでもfalse
            this.modalElement.addEventListener('hidden.bs.modal', () => {
                resolve(false);
            }, { once: true });
            
            this.modal.show();
        });
    }

    /**
     * アラートダイアログを表示（OKボタンのみ）
     * @param {string} message - 表示するメッセージ
     * @param {string} title - モーダルのタイトル（デフォルト: '通知'）
     * @param {Object} options - オプション
     * @param {string} options.confirmText - OKボタンのテキスト（デフォルト: 'OK'）
     * @param {string} options.confirmClass - OKボタンのクラス（デフォルト: 'btn-primary'）
     * @returns {Promise<void>}
     */
    alert(message, title = null, options = {}) {
        return new Promise((resolve) => {
            const {
                confirmText = 'OK',
                confirmClass = 'btn-primary'
            } = options;

            const defaultTitle = t('common_notice') || '通知';
            document.getElementById('commonModalLabel').textContent = title || defaultTitle;
            document.getElementById('commonModalBody').textContent = message;
            
            const confirmBtn = document.getElementById('commonModalConfirm');
            const cancelBtn = document.getElementById('commonModalCancel');
            
            confirmBtn.textContent = confirmText;
            
            // キャンセルボタンを非表示
            cancelBtn.style.display = 'none';
            
            // ボタンのクラスをリセット
            confirmBtn.className = `btn ${confirmClass}`;
            
            // イベントリスナーをクリア
            const newConfirmBtn = confirmBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
            
            // 新しいイベントリスナーを追加
            newConfirmBtn.addEventListener('click', () => {
                this.modal.hide();
                resolve();
            });
            
            // モーダル外クリック・ESCキーでも閉じる
            this.modalElement.addEventListener('hidden.bs.modal', () => {
                cancelBtn.style.display = ''; // 次回のために表示を戻す
                resolve();
            }, { once: true });
            
            this.modal.show();
        });
    }

    /**
     * 成功メッセージを表示
     * @param {string} message - 表示するメッセージ
     * @param {string} title - モーダルのタイトル（デフォルト: '成功'）
     * @returns {Promise<void>}
     */
    success(message, title = null) {
        const defaultTitle = t('common_success') || '成功';
        return this.alert(message, title || defaultTitle, {
            confirmClass: 'btn-success'
        });
    }

    /**
     * エラーメッセージを表示
     * @param {string} message - 表示するメッセージ
     * @param {string} title - モーダルのタイトル（デフォルト: 'エラー'）
     * @returns {Promise<void>}
     */
    error(message, title = null) {
        const defaultTitle = t('common_error') || 'エラー';
        return this.alert(message, title || defaultTitle, {
            confirmClass: 'btn-danger'
        });
    }

    /**
     * 警告メッセージを表示
     * @param {string} message - 表示するメッセージ
     * @param {string} title - モーダルのタイトル（デフォルト: '警告'）
     * @returns {Promise<void>}
     */
    warning(message, title = null) {
        const defaultTitle = t('common_warning') || '警告';
        return this.alert(message, title || defaultTitle, {
            confirmClass: 'btn-warning'
        });
    }

    /**
     * 削除確認ダイアログを表示
     * @param {string} message - 表示するメッセージ
     * @param {string} title - モーダルのタイトル（デフォルト: '削除確認'）
     * @returns {Promise<boolean>}
     */
    confirmDelete(message = null, title = null) {
        const defaultMessage = t('common_delete_confirm') || '本当に削除しますか？';
        const defaultTitle = t('common_delete_confirm_title') || '削除確認';
        
        return this.confirm(
            message || defaultMessage,
            title || defaultTitle,
            {
                confirmText: t('common_delete') || '削除',
                confirmClass: 'btn-danger'
            }
        );
    }
}

// グローバルインスタンスを作成
// このスクリプトはBootstrap JSの後に読み込まれるため、bootstrapは必ず定義されている
const modal = new CommonModal();
