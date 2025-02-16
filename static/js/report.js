// Markdown 渲染設置
marked.setOptions({
    gfm: true,
    breaks: true,
    sanitize: false,
    smartLists: true,
    smartypants: true
});

// 更新報告內容的函數
function updateReport(reportContent) {
    const reportContainer = document.getElementById('reportContainer');
    if (!reportContainer) return;

    // 使用 marked 渲染 Markdown
    reportContainer.innerHTML = marked(reportContent);

    // 處理表格樣式
    const tables = reportContainer.getElementsByTagName('table');
    Array.from(tables).forEach(table => {
        table.classList.add('table', 'table-bordered');
    });

    // 處理 emoji
    reportContainer.innerHTML = reportContainer.innerHTML.replace(
        /([\uD800-\uDBFF][\uDC00-\uDFFF])/g,
        '<span class="emoji">$1</span>'
    );
}

// 監聽報告更新
document.addEventListener('DOMContentLoaded', () => {
    // 假設報告內容來自 API 響應
    fetch('/care-record/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateReport(data.report);
        }
    })
    .catch(error => console.error('Error:', error));
});

// 添加列印功能
document.getElementById('printReport')?.addEventListener('click', () => {
    window.print();
}); 