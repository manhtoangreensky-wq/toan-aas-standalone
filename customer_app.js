// XÁC THỰC
        const USER_ID = localStorage.getItem('user_id');
        const ROLE = localStorage.getItem('role');
        const USERNAME = localStorage.getItem('username') || 'Khách hàng';

        if(!USER_ID) { window.location.href = '/login'; }

        document.getElementById('user-display-name').innerText = USERNAME;
        document.getElementById('user-avatar-text').innerText = USERNAME.charAt(0).toUpperCase();

        if(ROLE === 'admin') {
            document.getElementById('admin-panel-card').classList.remove('hidden');
        }

        function toggleModal(id) {
            document.getElementById(id).classList.toggle('hidden');
        }

        function logout() {
            localStorage.clear();
            window.location.href = '/login';
        }

        // HỆ THỐNG TOAST NOTIFICATION MƯỢT MÀ
        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            let bgColor = type === 'success' ? 'bg-slate-800' : (type === 'warning' ? 'bg-orange-500' : 'bg-red-500');
            let icon = type === 'success' ? '<i class="fas fa-check-circle text-emerald-400 mr-2"></i>' : '<i class="fas fa-exclamation-triangle text-white mr-2"></i>';
            toast.className = `toast-enter ${bgColor} text-white px-6 py-4 rounded-xl shadow-2xl flex items-center max-w-sm pointer-events-auto`;
            toast.innerHTML = `${icon} <span class="text-sm font-medium leading-snug">${message}</span>`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.classList.replace('toast-enter', 'toast-exit');
                setTimeout(() => toast.remove(), 300);
            }, 3500);
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast(`Đã copy link: ${text}`, 'success');
            });
        }

        // --- GỌI API THẬT: GỬI FEEDBACK ---
        async function submitFeedback() {
            const content = document.getElementById('fb-content').value;
            if(!content.trim()) return showToast('Vui lòng nhập nội dung góp ý!', 'warning');
            
            try {
                const res = await fetch('/api/v1/customer/feedback', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: USER_ID, content: content })
                });
                const data = await res.json();
                if(data.success) {
                    showToast(data.message, 'success');
                    document.getElementById('fb-content').value = '';
                    toggleModal('modal-feedback');
                } else {
                    showToast(data.message, 'error');
                }
            } catch(e) { showToast('Lỗi mất kết nối mạng!', 'error'); }
        }

        // --- GỌI API THẬT: TẠO LINK PAYOS ---
        async function processPayment(btn, amountVND, xu) {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = `<div class="text-center w-full py-1"><i class="fas fa-spinner fa-spin text-emerald-600 text-xl"></i></div>`;
            btn.disabled = true;
            
            try {
                const res = await fetch('/api/v1/customer/payos/create-link', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: USER_ID, amount_vnd: amountVND, xu_nhan: xu })
                });
                const data = await res.json();
                if(data.success) {
                    showToast(`Khởi tạo thành công! Đang chuyển hướng...`, 'success');
                    window.location.href = data.checkout_url; // Chuyển thẳng sang cổng QR PayOS
                } else {
                    showToast(data.message, 'error');
                    btn.innerHTML = originalHTML;
                    btn.disabled = false;
                }
            } catch(e) {
                showToast('Lỗi mạng khi tạo mã PayOS.', 'error');
                btn.innerHTML = originalHTML;
                btn.disabled = false;
            }
        }

        // --- GỌI API THẬT: CÁC TOOL AI (Trừ Xu thật) ---
        async function simulateProcess(modalId, toolType, cost, promptId) {
            const promptText = document.getElementById(promptId) ? document.getElementById(promptId).value : "Mặc định";
            toggleModal(modalId);
            showToast(`Đang gửi yêu cầu... <span class="bg-slate-700 text-white px-2 py-0.5 rounded text-[10px] ml-2 font-bold">-${cost} Xu</span>`, 'warning');
            
            try {
                const res = await fetch('/api/v1/customer/ai/process', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: USER_ID, tool_type: toolType, cost: parseInt(cost), prompt: promptText })
                });
                const data = await res.json();
                if(data.success) {
                    showToast(data.message, 'success');
                    // Cập nhật lại số dư trên màn hình ngay lập tức
                    document.getElementById('wallet-balance-display').innerText = data.remaining_xu.toLocaleString('vi-VN');
                    document.getElementById('modal-current-balance').innerText = data.remaining_xu.toLocaleString('vi-VN');
                } else {
                    showToast(data.message, 'error'); // Báo lỗi nếu không đủ Xu
                }
            } catch(e) { showToast('Lỗi gọi API AI.', 'error'); }
        }

        // Thay đổi các nút bấm trong HTML để gọi hàm mới
        // Nút Media: onclick="simulateProcess('modal-media', 'media', 10, null)"
        // Nút Video: onclick="simulateProcess('modal-video', 'video', 200, 'video-prompt-id')"
        // Nút Voice: onclick="simulateProcess('modal-voice', 'voice', 50, 'voice-prompt-id')"

        // LOAD DATA TỪ API
        async function loadData() {
            try {
                const resAuth = await fetch(`/api/v1/auth/me/${USER_ID}`);
                const dataAuth = await resAuth.json();
                if(dataAuth.success) {
                    const balance = dataAuth.credits.toLocaleString('vi-VN');
                    document.getElementById('wallet-balance-display').innerText = balance;
                    document.getElementById('modal-current-balance').innerText = balance;
                }
                const resStats = await fetch('/api/v1/erp/dashboard-stats');
                const dataStats = await resStats.json();
                if(dataStats.success) {
                    document.getElementById('stat-projects').innerText = dataStats.data.total_projects;
                }
            } catch(e) { console.error("Lỗi lấy dữ liệu:", e); }
        }

        document.addEventListener('DOMContentLoaded', loadData);