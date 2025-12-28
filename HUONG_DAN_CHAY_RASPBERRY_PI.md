# 🍓 Hướng Dẫn Chạy File raspberry_pi_upload.py

## 📋 Yêu Cầu Trước Khi Chạy

### 1. Cài đặt Python packages

Trên Raspberry Pi, chạy các lệnh sau:

```bash
# Cài đặt pip nếu chưa có
sudo apt-get update
sudo apt-get install python3-pip

# Cài đặt các thư viện cần thiết
pip3 install requests opencv-python pillow
```

**Hoặc cài từng package:**
```bash
pip3 install requests
pip3 install opencv-python
pip3 install pillow
```

### 2. Kiểm tra USB Camera

```bash
# Kiểm tra camera đã được nhận diện chưa
lsusb

# Hoặc kiểm tra với v4l2
v4l2-ctl --list-devices
```

### 3. Cấu hình Script

Mở file `raspberry_pi_upload.py` và sửa các thông tin sau:

```python
# Dòng 18: Thay đổi IP server của bạn
SERVER_URL = "http://192.168.101.36:5000"  # ← SỬA IP NÀY (hoặc IP server của bạn)

# Dòng 19: API key (phải khớp với server)
API_KEY = "raspberry_pi_key_123"  # ← Kiểm tra xem có đúng không

# Dòng 20: ID thiết bị (tùy chọn)
DEVICE_ID = "RASPBERRY_PI_001"  # ← Có thể đổi tên

# Dòng 23: ImgBB API Key (đã có sẵn)
IMGBB_API_KEY = '42e11ba3563b75735c958d96aa6aea3f'  # ← Đã cấu hình sẵn
```

**Cách tìm IP server:**
- Trên Windows: Mở Command Prompt → `ipconfig` → Tìm `IPv4 Address`
- Trên Linux/Mac: Mở Terminal → `ifconfig` hoặc `ip addr`

### 4. Đảm bảo Server đang chạy

Trên máy server, chạy:
```bash
# Windows
CHAY_SERVER.bat

# Hoặc Linux/Mac
python3 app.py
```

Kiểm tra server đang chạy bằng cách mở trình duyệt:
```
http://localhost:5000/health
```

---

## 🚀 Cách Chạy Script

### Chạy trực tiếp:

```bash
python3 raspberry_pi_upload.py
```

### Hoặc với quyền root (nếu cần):

```bash
sudo python3 raspberry_pi_upload.py
```

---

## 📝 Quy Trình Chạy Script

Khi chạy, script sẽ thực hiện các bước sau:

1. **Kiểm tra kết nối server** 
   - ✅ Server đang hoạt động
   - ⚠️ Không kết nối được (nhưng vẫn thử upload)

2. **Chụp ảnh từ USB camera**
   - Thử camera index 0, 1, 2...
   - Nếu không có camera, thử load từ file `test_image.jpg`

3. **Nhận dạng biển số** (placeholder)
   - Hiện tại trả về biển số mẫu: `51A-TEST01`
   - ⚠️ Cần tích hợp thư viện nhận dạng thực tế

4. **Upload ảnh lên ImgBB**
   - Upload ảnh lên ImgBB API
   - Lấy URL ảnh (ví dụ: `https://i.ibb.co/...`)

5. **Gửi dữ liệu lên server**
   - Gửi URL ảnh từ ImgBB
   - Gửi thông tin: biển số, hướng, trọng lượng, v.v.

---

## ✅ Kết Quả Mong Đợi

Nếu thành công, bạn sẽ thấy:

```
============================================================
🍓 RASPBERRY PI - GỬI ẢNH TỪ USB CAMERA LÊN SERVER
============================================================

🔗 Kiểm tra kết nối server: http://192.168.101.36:5000
✅ Server đang hoạt động!

📸 Bước 1: Chụp ảnh từ USB camera...
📷 Đang mở camera index 0...
✅ Chụp ảnh thành công! Kích thước: 123456 bytes

🔍 Bước 2: Nhận dạng biển số...
🔍 Đang nhận dạng biển số...
⚠️  TODO: Tích hợp thư viện nhận dạng biển số
   Biển số: 51A-TEST01

📤 Bước 3: Gửi ảnh lên server...
📤 Đang upload ảnh lên ImgBB...
✅ Upload lên ImgBB thành công!
   📸 URL: https://i.ibb.co/xxxxx/image.jpg

📤 Đang gửi dữ liệu lên server: http://192.168.101.36:5000/api/upload
✅ Thành công!
   🆔 Record ID: 123
   🚗 Biển số: 51A-TEST01
   ⚖️  Khối lượng: 3.5 tấn
   📸 Ảnh URL: https://i.ibb.co/xxxxx/image.jpg
   🕐 Thời gian: 2025-11-02T21:40:35

============================================================
✅ HOÀN TẤT! Dữ liệu đã được lưu vào server.
   Xem tại: http://192.168.101.36:5000/dashboard
============================================================
```

---

## ❌ Xử Lý Lỗi

### Lỗi: "Không thể mở camera"
```bash
# Kiểm tra camera
lsusb
v4l2-ctl --list-devices

# Thử camera index khác trong code
# Sửa dòng 232: for camera_idx in range(3):
```

### Lỗi: "Không thể kết nối đến server"
- Kiểm tra IP server có đúng không
- Kiểm tra server có đang chạy không
- Kiểm tra firewall/network

### Lỗi: "Invalid API key"
- Kiểm tra `API_KEY` trong script có khớp với server không
- Mặc định: `raspberry_pi_key_123`

### Lỗi: "Không thể upload lên ImgBB"
- Script sẽ tự động fallback về cách gửi file trực tiếp
- Kiểm tra kết nối internet
- Kiểm tra ImgBB API key

---

## 🔄 Chạy Tự Động (Cron Job)

Để chạy tự động mỗi phút:

```bash
# Mở crontab
crontab -e

# Thêm dòng sau (chạy mỗi phút)
* * * * * /usr/bin/python3 /path/to/raspberry_pi_upload.py >> /var/log/raspberry_upload.log 2>&1
```

Hoặc chạy mỗi 5 phút:
```bash
*/5 * * * * /usr/bin/python3 /path/to/raspberry_pi_upload.py >> /var/log/raspberry_upload.log 2>&1
```

---

## 📌 Lưu Ý Quan Trọng

1. **IP Server**: Phải sửa `SERVER_URL` thành IP thực tế của máy server
2. **API Key**: Phải khớp với server (`raspberry_pi_key_123`)
3. **Camera**: Đảm bảo USB camera đã được cắm và nhận diện
4. **Network**: Raspberry Pi và Server phải cùng mạng hoặc có thể kết nối
5. **ImgBB API**: Đã được cấu hình sẵn, không cần thay đổi

---

## 🆘 Hỗ Trợ

Nếu gặp vấn đề, kiểm tra:
- Log file (nếu có)
- Kết nối mạng
- Server đang chạy
- Camera hoạt động
- Python packages đã cài đầy đủ

