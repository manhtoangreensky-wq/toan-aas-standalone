// Tạo link thanh toán PayOS
        async function createPayment() {
            const amount = parseInt(document.getElementById('topup-amount').value);
            const btn = document.getElementById('btn-pay');
            const msgBox = document.getElementById('msg');

            if(!amount || amount < 10000) {
                msgBox.innerText = "Số tiền nạp tối thiểu là 10.000 VNĐ!";
                msgBox.className = "text-center text-sm font-semibold text-red-500 block mt-4";
                msgBox.classList.remove("hidden");
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang kết nối ngân hàng...';
            msgBox.classList.add("hidden");

            try {
                const res = await fetch('/api/v1/billing/create-payment-link', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: USER_ID,
                        payment_type: "topup_xu", // BẮT BUỘC PHẢI CÓ DÒNG NÀY ĐỂ KHÔNG BỊ LỖI
                        package_id: "CUSTOM_TOPUP",
                        amount: amount
                    })
                });
                const data = await res.json();
                
                if(data.success && data.checkoutUrl) {
                    msgBox.innerText = "Đang chuyển hướng sang cổng thanh toán...";
                    msgBox.className = "text-center text-sm font-semibold text-emerald-600 block mt-4";
                    msgBox.classList.remove("hidden");
                    // Chuyển thẳng trang hiện tại sang PayOS để quét mã
                    window.location.href = data.checkoutUrl;
                } else {
                    msgBox.innerText = "Lỗi tạo mã QR: " + (data.message || "Lỗi máy chủ");
                    msgBox.className = "text-center text-sm font-semibold text-red-500 block mt-4";
                    msgBox.classList.remove("hidden");
                }
            } catch (error) {
                msgBox.innerText = "Lỗi kết nối máy chủ PayOS!";
                msgBox.className = "text-center text-sm font-semibold text-red-500 block mt-4";
                msgBox.classList.remove("hidden");
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-bolt"></i> Tạo Mã QR Thanh Toán';
            }
        }