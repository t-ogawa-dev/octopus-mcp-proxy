/**
 * Resource新規登録画面
 */

let uploadedResourceContent = null;

// ファイル入力タイプ切り替え
function toggleResourceInputType() {
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    const textInput = document.getElementById('resource-text-input');
    const fileInput = document.getElementById('resource-file-input');
    const contentTextarea = document.getElementById('content');
    
    if (inputType === 'file') {
        if (textInput) textInput.style.display = 'none';
        if (fileInput) fileInput.style.display = 'block';
        if (contentTextarea) contentTextarea.removeAttribute('required');
    } else {
        if (textInput) textInput.style.display = 'block';
        if (fileInput) fileInput.style.display = 'none';
        if (contentTextarea) contentTextarea.setAttribute('required', 'required');
    }
}

// ファイルアップロード処理
function handleResourceFileUpload(file) {
    // 引数がない場合はinputから取得
    if (!file) {
        const fileInput = document.getElementById('resource_file');
        file = fileInput?.files[0];
    }
    
    if (!file) return;
    
    // ファイルサイズチェック (20KB)
    if (file.size > 20 * 1024) {
        modal.error(t('resource_file_too_large') || 'ファイルサイズが20KBを超えています');
        const fileInput = document.getElementById('resource_file');
        if (fileInput) fileInput.value = '';
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        uploadedResourceContent = e.target.result;
        
        // プレビュー表示
        const previewDiv = document.getElementById('resource-file-preview');
        const fileNameSpan = document.getElementById('resource-file-name');
        const fileSizeSpan = document.getElementById('resource-file-size');
        const dropZone = document.getElementById('resource-drop-zone');
        
        if (previewDiv) previewDiv.style.display = 'block';
        if (dropZone) dropZone.style.display = 'none';
        if (fileNameSpan) fileNameSpan.textContent = file.name;
        if (fileSizeSpan) fileSizeSpan.textContent = `${(file.size / 1024).toFixed(1)} KB`;
        
        // MIMEタイプ自動設定
        const mimeTypeSelect = document.getElementById('mime_type');
        if (mimeTypeSelect) {
            const ext = file.name.split('.').pop().toLowerCase();
            const mimeMap = {
                'txt': 'text/plain',
                'md': 'text/markdown',
                'json': 'application/json',
                'html': 'text/html',
                'csv': 'text/csv',
                'xml': 'application/xml',
                'yaml': 'text/yaml',
                'yml': 'text/yaml'
            };
            if (mimeMap[ext]) {
                mimeTypeSelect.value = mimeMap[ext];
            }
        }
        
        generateResourcePreview();
    };
    reader.readAsText(file);
}

// ファイルクリア
function clearResourceFile() {
    const fileInput = document.getElementById('resource_file');
    const previewDiv = document.getElementById('resource-file-preview');
    const dropZone = document.getElementById('resource-drop-zone');
    
    if (fileInput) fileInput.value = '';
    if (previewDiv) previewDiv.style.display = 'none';
    if (dropZone) dropZone.style.display = 'block';
    uploadedResourceContent = null;
    generateResourcePreview();
}

// リソースプレビュー生成
function generateResourcePreview() {
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    const previewOutput = document.getElementById('resource-preview-output');
    
    if (!previewOutput) return;
    
    let content = '';
    if (inputType === 'file' && uploadedResourceContent) {
        content = uploadedResourceContent;
    } else {
        content = document.getElementById('content')?.value || '';
    }
    
    if (content) {
        // 最大500文字でトランケート
        if (content.length > 500) {
            previewOutput.textContent = content.substring(0, 500) + '\n\n... (以下省略)';
        } else {
            previewOutput.textContent = content;
        }
    } else {
        previewOutput.textContent = '(コンテンツなし)';
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    
    // コンテンツの取得
    let content = '';
    if (inputType === 'file') {
        if (!uploadedResourceContent) {
            await modal.error(t('resource_file_required') || 'ファイルを選択してください');
            return;
        }
        content = uploadedResourceContent;
    } else {
        content = formData.get('content');
        if (!content) {
            await modal.error(t('resource_content_required') || 'コンテンツを入力してください');
            return;
        }
        // 文字数制限チェック (10,000文字)
        if (content.length > 10000) {
            await modal.error(t('resource_content_too_long') || 'コンテンツが10,000文字を超えています');
            return;
        }
        // テキスト入力のサイズチェック (20KB)
        const contentSize = new Blob([content]).size;
        if (contentSize > 20 * 1024) {
            await modal.error(t('resource_content_too_large') || 'コンテンツサイズが20KBを超えています');
            return;
        }
    }
    
    const data = {
        name: formData.get('name'),
        mime_type: formData.get('mime_type'),
        content: content,
        description: formData.get('description') || '',
        access_control: 'public',  // 常にpublic
        is_enabled: true  // 常に有効
    };
    
    try {
        const result = await AppApi.request('/api/resources', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        await modal.success(t('resource_created_success'));
        window.location.href = `/resources/${result.id}`;
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

// Initialize
(async () => {
    await initLanguageSwitcher();

    document.addEventListener('click', (event) => {
        const action = event.target.closest('[data-action]')?.dataset.action;
        if (action === 'select-file') document.getElementById('resource_file').click();
        if (action === 'clear-file') clearResourceFile();
    });
    document.addEventListener('change', (event) => {
        const action = event.target.dataset.action;
        if (action === 'toggle-input-type') toggleResourceInputType();
        if (action === 'file-input' && event.target.files[0]) handleResourceFileUpload(event.target.files[0]);
    });
    document.addEventListener('input', (event) => {
        if (event.target.dataset.action === 'resource-content-input') {
            generateResourcePreview();
            updateCharCount();
        }
    });
    
    document.getElementById('resource-form').addEventListener('submit', handleSubmit);
    
    // Setup drag and drop
    const dropZone = document.getElementById('resource-drop-zone');
    if (dropZone) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        // Highlight drop zone when dragging over
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.backgroundColor = '#e6f7ff';
                dropZone.style.borderColor = '#1890ff';
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.backgroundColor = '#f7fafc';
                dropZone.style.borderColor = '#cbd5e0';
            });
        });
        
        // Handle dropped files
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleResourceFileUpload(files[0]);
            }
        });
        
        // Click to select file
        dropZone.addEventListener('click', (e) => {
            // ボタンクリックでない場合のみ
            if (e.target.tagName !== 'BUTTON') {
                document.getElementById('resource_file')?.click();
            }
        });
    }
    
    // 文字数カウンタ更新
    updateCharCount();
})();

// 文字数カウンタ更新関数
function updateCharCount() {
    const contentTextarea = document.getElementById('content');
    const charCountElement = document.getElementById('char-count');
    
    if (contentTextarea && charCountElement) {
        const currentLength = contentTextarea.value.length;
        const maxLength = 10000;
        charCountElement.textContent = `${currentLength.toLocaleString()}/${maxLength.toLocaleString()}`;
        
        // 90%を超えたら警告色に
        if (currentLength > maxLength * 0.9) {
            charCountElement.style.color = '#dc3545';
        } else {
            charCountElement.style.color = '#6c757d';
        }
    }
}
