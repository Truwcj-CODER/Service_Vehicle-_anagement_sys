# 🍓 Hướng Dẫn Sử Dụng Raspberry Pi với USB Camera

Hướng dẫn chi tiết để chụp ảnh từ USB camera trên Raspberry Pi và gửi lên server.

---

## 📋 Yêu Cầu

- Raspberry Pi (bất kỳ model nào)
- USB Camera (webcam USB)
- Kết nối mạng (WiFi hoặc Ethernet)
- Python 3.x

---

## 🔧 Cài Đặt

### Bước 1: Cài đặt Python packages

```bash
pip3 install requests opencv-python pillow
```

Hoặc trên Raspberry Pi:

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-opencv
pip3 install requests pillow
```

### Bước 2: Cấu hình script

Mở file `raspberry_pi_upload.py` và sửa các thông tin sau:

```python
# Thay đổi IP này thành IP của server của bạn
SERVER_URL = "http://192.168.1.100:5000"  # ← SỬA IP NÀY

# API Key (phải khớp với server)
API_KEY = "raspberry_pi_key_123"

# ID thiết bị (tùy chọn)
DEVICE_ID = "RASPBERRY_PI_001"
```

**Cách tìm IP server:**
- Trên Windows: Mở Command Prompt, gõ `ipconfig`, tìm `IPv4 Address`
- Trên Linux/Mac: Mở Terminal, gõ `ifconfig` hoặc `ip addr`

---

## 📸 Sử Dụng

### Chạy script

```bash
python3 raspberry_pi_upload.py
```

Script sẽ:
1. ✅ Kiểm tra kết nối server
2. 📷 Chụp ảnh từ USB camera
3. 🔍 Nhận dạng biển số (placeholder - cần tích hợp thư viện thực tế)
4. 📤 Gửi ảnh và dữ liệu lên server

---

## 🔌 API Endpoints

### 1. Upload ảnh trực tiếp (Khuyến nghị)

**Endpoint:** `POST /api/upload-image`

**Content-Type:** `multipart/form-data`

**Parameters:**
- `license_plate` (required): Biển số xe
- `direction` (optional): "IN" hoặc "OUT" (mặc định: "IN")
- `vehicle_weight` (optional): Trọng lượng xe (tấn)
- `device_id` (optional): ID thiết bị
- `notes` (optional): Ghi chú
- `api_key` (required): API key để xác thực
- `image` (required): File ảnh (JPEG, PNG, ...)

**Example với curl:**
```bash
curl -X POST "http://192.168.1.100:5000/api/upload-image" \
  -F "license_plate=29A-12345" \
  -F "direction=IN" \
  -F "vehicle_weight=5.5" \
  -F "device_id=RASPBERRY_PI_001" \
  -F "api_key=raspberry_pi_key_123" \
  -F "image=@/path/to/image.jpg"
```

**Example với Python:**
```python
import requests

files = {'image': open('image.jpg', 'rb')}
data = {
    'license_plate': '29A-12345',
    'direction': 'IN',
    'vehicle_weight': '5.5',
    'api_key': 'raspberry_pi_key_123'
}

response = requests.post('http://192.168.1.100:5000/api/upload-image', 
                        files=files, data=data)
print(response.json())
```

### 2. Upload với base64 (Backup)

**Endpoint:** `POST /api/upload`

**Content-Type:** `application/json`

**Body:**
```json
{
  "license_plate": "29A-12345",
  "direction": "IN",
  "vehicle_weight": 5.5,
  "device_id": "RASPBERRY_PI_001",
  "image_base64": "base64_encoded_image_string",
  "api_key": "raspberry_pi_key_123"
}
```

---

## 🐛 Xử Lý Lỗi

### ❌ Lỗi: Không thể mở camera

**Nguyên nhân:** Camera chưa được cắm hoặc không được nhận diện

**Giải pháp:**
1. Kiểm tra camera đã được cắm vào USB
2. Kiểm tra camera hoạt động:
   ```bash
   lsusb  # Xem danh sách USB devices
   ```
3. Thử camera index khác trong script (0, 1, 2, ...)

### ❌ Lỗi: Không thể kết nối đến server

**Nguyên nhân:** Server chưa chạy hoặc IP sai

**Giải pháp:**
1. Kiểm tra server đang chạy:
   ```bash
   # Trên server
   curl http://localhost:5000/health
   ```
2. Kiểm tra IP server đúng trong script
3. Kiểm tra firewall không chặn port 5000
4. Kiểm tra Raspberry Pi và server cùng mạng

### ❌ Lỗi: Invalid API key

**Nguyên nhân:** API key không khớp

**Giải pháp:**
1. Kiểm tra API key trong script khớp với server
2. Mặc định: `raspberry_pi_key_123`

### ❌ Lỗi: ModuleNotFoundError

**Nguyên nhân:** Thiếu Python packages

**Giải pháp:**
```bash
pip3 install requests opencv-python pillow
```

---

## 🔄 Tự Động Hóa

### Chạy tự động mỗi khi có xe

Tạo file `auto_capture.py`:

```python
#!/usr/bin/env python3
import time
from raspberry_pi_upload import capture_image_with_camera, upload_data_file, detect_license_plate

# Giả sử có cảm biến phát hiện xe
def detect_vehicle():
    # TODO: Tích hợp cảm biến thực tế
    # Ví dụ: GPIO, cảm biến hồng ngoại, v.v.
    return True  # Placeholder

while True:
    if detect_vehicle():
        print("🚗 Phát hiện xe!")
        
        # Chụp ảnh
        image_data = capture_image_with_camera()
        if image_data:
            # Nhận dạng biển số
            license_plate = detect_license_plate(image_data)
            
            # Upload
            upload_data_file(license_plate, image_data, direction="IN")
    
    time.sleep(1)  # Chờ 1 giây trước khi kiểm tra lại
```

### Chạy script tự động khi khởi động

Thêm vào `/etc/rc.local`:

```bash
sudo nano /etc/rc.local
```

Thêm dòng trước `exit 0`:

```bash
python3 /path/to/raspberry_pi_upload.py &
```

---

## 📝 Tích Hợp Nhận Dạng Biển Số

Hiện tại script dùng placeholder cho nhận dạng biển số. Để tích hợp thực tế:

### Option 1: EasyOCR

```bash
pip3 install easyocr
```

```python
import easyocr

reader = easyocr.Reader(['vi', 'en'])
results = reader.readtext(image)
# Xử lý results để lấy biển số
```

### Option 2: PaddleOCR

```bash
pip3 install paddlepaddle paddleocr
```

```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang='vi')
results = ocr.ocr(image, cls=True)
# Xử lý results
```

### Option 3: YOLOv8 + OCR

Tích hợp YOLOv8 để detect biển số, sau đó dùng OCR để đọc.

---

## 🔐 Bảo Mật

⚠️ **Lưu ý:** API key hiện tại là mặc định và không an toàn cho production!

**Để bảo mật hơn:**
1. Thay đổi API key trong `app.py` và `raspberry_pi_upload.py`
2. Sử dụng HTTPS thay vì HTTP
3. Thêm rate limiting
4. Sử dụng JWT token thay vì API key đơn giản

---

## 📊 Xem Kết Quả

Sau khi upload thành công:
1. Mở trình duyệt
2. Truy cập: `http://SERVER_IP:5000/dashboard`
3. Đăng nhập (mặc định: admin / 22138109)
4. Xem ảnh đã upload trong bảng dữ liệu

---

## 💡 Tips

1. **Test camera trước:**
   ```bash
   python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera FAIL')"
   ```

2. **Test kết nối server:**
   ```bash
   curl http://SERVER_IP:5000/health
   ```

3. **Xem log chi tiết:** Chạy script với Python để xem output chi tiết

4. **Lưu ảnh local:** Sửa script để lưu ảnh vào thư mục trước khi upload (backup)

---

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra log trong script
2. Kiểm tra server log
3. Kiểm tra kết nối mạng
4. Kiểm tra camera và USB ports

---

**Chúc bạn thành công! 🚀**

