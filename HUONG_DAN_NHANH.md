# 🚀 Hướng Dẫn Nhanh - Raspberry Pi Upload Ảnh

## Bước 1: Chạy Server (Trên máy chủ Windows)

```bash
# Cách 1: Double-click file
CHAY_SERVER.bat

# Cách 2: Chạy thủ công
python app.py
```

✅ Server sẽ chạy tại: `http://localhost:5000` hoặc `http://YOUR_IP:5000`

---

## Bước 2: Copy File Sang Raspberry Pi

### Cách 1: Dùng USB
1. Copy file `raspberry_pi_upload.py` vào USB
2. Cắm USB vào Raspberry Pi
3. Copy file từ USB vào thư mục trên Pi

### Cách 2: Dùng SCP (từ máy Windows)
```bash
# Từ Command Prompt hoặc PowerShell
scp raspberry_pi_upload.py pi@RASPBERRY_PI_IP:/home/pi/
```

### Cách 3: Dùng FileZilla hoặc WinSCP
- Kết nối SFTP đến Raspberry Pi
- Upload file `raspberry_pi_upload.py`

---

## Bước 3: Trên Raspberry Pi

### 3.1. Tìm IP của máy chủ Windows

Trên máy Windows, mở Command Prompt:
```bash
ipconfig
```

Tìm `IPv4 Address` (ví dụ: `192.168.1.100`)

### 3.2. Sửa file `raspberry_pi_upload.py`

```bash
nano raspberry_pi_upload.py
```

Tìm dòng:
```python
SERVER_URL = "http://192.168.1.100:5000"  # Thay bằng IP server thực tế
```

Sửa thành IP của máy chủ Windows:
```python
SERVER_URL = "http://192.168.1.100:5000"  # ← SỬA IP NÀY
```

Lưu: `Ctrl + O`, Enter, `Ctrl + X`

### 3.3. Cài đặt packages

```bash
pip3 install requests opencv-python pillow
```

Hoặc:
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-opencv
pip3 install requests pillow
```

### 3.4. Chạy script

```bash
python3 raspberry_pi_upload.py
```

---

## ✅ Kết Quả

Nếu thành công, bạn sẽ thấy:
```
✅ HOÀN TẤT! Dữ liệu đã được lưu vào server.
   Xem tại: http://192.168.1.100:5000/dashboard
```

Sau đó mở trình duyệt trên máy chủ:
- URL: `http://localhost:5000/dashboard`
- Đăng nhập: `admin` / `1`
- Click "Xem ảnh" để xem ảnh đã upload

---

## 🔧 Kiểm Tra

### Test kết nối từ Pi đến Server:
```bash
curl http://YOUR_SERVER_IP:5000/health
```

Nếu thấy `{"status":"healthy","database":"connected"}` → Kết nối OK!

### Test camera trên Pi:
```bash
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"
```

---

## ⚠️ Lưu Ý

1. **Server phải chạy trước** khi chạy script trên Pi
2. **Pi và Server phải cùng mạng** (cùng WiFi hoặc cùng router)
3. **Firewall Windows** có thể chặn port 5000, cần mở port hoặc tắt firewall tạm thời
4. **Camera USB** phải được cắm vào Pi trước khi chạy script

---

## 🐛 Lỗi Thường Gặp

### ❌ Không kết nối được server
- Kiểm tra IP server đúng chưa
- Kiểm tra server đang chạy chưa
- Kiểm tra firewall Windows

### ❌ Không chụp được ảnh
- Kiểm tra camera đã cắm USB chưa
- Thử camera index khác (0, 1, 2...)

### ❌ ModuleNotFoundError
- Chạy: `pip3 install requests opencv-python pillow`

---

**Chúc bạn thành công! 🎉**

