# 🤖 HƯỚNG DẪN ESP32 CHỤP ẢNH VÀ UPLOAD LÊN SERVER

## 📋 TỔNG QUAN FLOW

```
ESP32-CAM → Chụp ảnh → Chuyển Base64 → Gửi HTTP POST → Server FastAPI 
    ↓                                                              ↓
    └─────────────────────────────────────────────────────────────┴→ Lưu vào Database
                                                                      ↓
                                                            Dashboard hiển thị ảnh
```

---

## 🔧 CẤU HÌNH ESP32

### 1. **Cài đặt Thư viện**

Mở **Arduino IDE** → **Tools** → **Manage Libraries**:

- ✅ `ArduinoJson` (bởi Benoit Blanchon) - Version 6.x
- ✅ `WiFi` (built-in ESP32)
- ✅ `HTTPClient` (built-in ESP32)
- ✅ `esp_camera.h` (built-in ESP32-CAM)

### 2. **Chọn Board**

- **Tools** → **Board** → **ESP32 Arduino** → **ESP32 Dev Module**
  - Hoặc **AI Thinker ESP32-CAM**
  - Hoặc **ESP32S3 Eye**

### 3. **Sửa Cấu hình trong Code**

Mở file `esp32_upload_example.ino` và sửa:

```cpp
// WiFi
const char* ssid = "TEN_WIFI_CUA_BAN";
const char* password = "MAT_KHAU_WIFI";

// Server (IP của máy chạy FastAPI)
const char* SERVER_URL = "http://192.168.1.100:5000/api/upload";

// Device ID
String device_id = "ESP32_CAM_001";
```

### 4. **Tìm IP Server**

Trên máy chạy server, chạy:
```bash
# Windows
ipconfig

# Linux/Mac
ifconfig
```

Lấy IP local (ví dụ: `192.168.1.100`) → Sửa vào code ESP32.

---

## 📤 QUY TRÌNH UPLOAD

### **Bước 1: ESP32 Chụp Ảnh**

```cpp
camera_fb_t* fb = esp_camera_fb_get();
// Ảnh lưu trong fb->buf, kích thước: fb->len
```

### **Bước 2: Chuyển Sang Base64**

```cpp
String imageBase64 = imageToBase64(fb->buf, fb->len);
```

### **Bước 3: Tạo JSON Payload**

```json
{
  "license_plate": "29A-12345",
  "direction": "IN",
  "vehicle_weight": 5.5,
  "device_id": "ESP32_CAM_001",
  "notes": "Uploaded from ESP32-CAM",
  "api_key": "raspberry_pi_key_123",
  "image_base64": "iVBORw0KGgoAAAANS..."
}
```

### **Bước 4: Gửi HTTP POST**

```cpp
HTTPClient http;
http.begin(SERVER_URL);
http.addHeader("Content-Type", "application/json");
int responseCode = http.POST(jsonPayload);
```

### **Bước 5: Server Xử Lý**

- FastAPI nhận JSON
- Decode base64 → Lưu ảnh vào `uploads/YYYY/MM/DD/`
- Lưu thông tin vào database `vehicle_records`
- Trả về `{"success": true, "id": 123}`

### **Bước 6: Xem Trong Dashboard**

- Vào `http://localhost:5000/dashboard`
- Tìm record mới
- Click **"Xem ảnh"** → Ảnh hiển thị!

---

## 🔍 KẾT NỐI CẢM BIẾN

### **Nhận Diện Biển Số (OCR)**

Có thể tích hợp:
- **EasyOCR** trên server (Python)
- **Tesseract OCR** trên server
- **Camera nhận diện** trên ESP32 (phức tạp hơn)

**Gợi ý:** Gửi ảnh lên → Server xử lý OCR → Lưu vào database

### **Cảm Biến Cân (Load Cell)**

```cpp
// Đọc từ HX711
float weight = readWeightSensor();  // Tấn
doc["vehicle_weight"] = weight;
```

### **Cảm Biến Phát Hiện Xe**

```cpp
// GPIO trigger
if (digitalRead(TRIGGER_PIN) == HIGH) {
  // Xe vào/ra → Chụp ảnh
  camera_fb_t* fb = capturePhoto();
  uploadToServer(licensePlate, direction, weight, fb);
}
```

---

## 📁 ĐƯỜNG DẪN ẢNH TRÊN SERVER

**Format:** `uploads/YYYY/MM/DD/bien_so_YYYYMMDD_HHMMSS.jpg`

**Ví dụ:**
- `uploads/2025/11/02/29A_12345_20251102_143000.jpg`

**URL truy cập:**
- `http://192.168.1.100:5000/uploads/2025/11/02/29A_12345_20251102_143000.jpg`

---

## 🐛 XỬ LÝ LỖI

### **Lỗi: Can't connect to server**

- ✅ Kiểm tra WiFi ESP32 đã kết nối chưa
- ✅ Kiểm tra IP server đúng chưa
- ✅ Đảm bảo server đang chạy (`python app.py`)
- ✅ Kiểm tra firewall không chặn port 5000

### **Lỗi: Out of memory**

- ✅ Giảm chất lượng ảnh: `config.jpeg_quality = 20;`
- ✅ Giảm độ phân giải: `config.frame_size = FRAMESIZE_VGA;`
- ✅ Tăng heap: `config.fb_count = 1;`

### **Lỗi: JSON too large**

- ✅ Nén ảnh trước khi encode
- ✅ Giảm kích thước ảnh
- ✅ Tăng buffer: `DynamicJsonDocument doc(100000);`

---

## 💡 VÍ DỤ CODE ĐẦY ĐỦ

File: `esp32_upload_example.ino` (đã có trong project)

**Cách sử dụng:**
1. Mở Arduino IDE
2. Load file `esp32_upload_example.ino`
3. Sửa WiFi + Server URL
4. Upload lên ESP32
5. Mở Serial Monitor (115200 baud)
6. Chờ trigger → Xem kết quả

---

## 🔄 TEST THỦ CÔNG

**Không có ESP32-CAM?** Dùng Raspberry Pi:

```bash
python raspberry_pi_upload.py
```

Script này sẽ:
- Chụp ảnh từ webcam (hoặc đọc từ file)
- Upload lên server
- Lưu vào database
- Xem được trong dashboard

---

## ✅ CHECKLIST TRƯỚC KHI CHẠY

- [ ] ESP32 kết nối WiFi thành công
- [ ] Server FastAPI đang chạy (`python app.py`)
- [ ] IP server đúng trong code ESP32
- [ ] API key khớp: `raspberry_pi_key_123`
- [ ] Camera ESP32-CAM khởi tạo thành công
- [ ] Database MySQL đang chạy
- [ ] Thư mục `uploads/` tồn tại

---

## 🎯 KẾT QUẢ

Sau khi ESP32 upload thành công:

1. ✅ **Ảnh lưu tại:** `Cursor/uploads/2025/11/02/xxx.jpg`
2. ✅ **Record trong database:** `vehicle_records` table
3. ✅ **Xem trong dashboard:** Click "Xem ảnh" → Hiển thị modal
4. ✅ **URL ảnh:** `http://server:5000/uploads/.../xxx.jpg`

**Chúc bạn thành công!** 🚀

