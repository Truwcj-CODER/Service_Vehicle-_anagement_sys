# 🚗 Hệ Thống Kiểm Soát Xe Ra Vào

Hệ thống quản lý và theo dõi xe ra vào với nhận dạng biển số và đo trọng lượng, lưu trữ dữ liệu vào MySQL.

---

## ✨ Tính năng

- 📸 Chụp ảnh và nhận dạng biển số xe
- ⚖️ Đo trọng lượng xe
- 🔄 Phân biệt xe vào (IN) và xe ra (OUT)
- 💾 Lưu trữ dữ liệu vào MySQL (XAMPP)
- 📊 Dashboard web để xem thống kê
- 🔌 API để nhận dữ liệu từ thiết bị (Raspberry Pi/ESP32)

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT VÀ SỬ DỤNG

### BƯỚC 1: Cài đặt Dependencies

```bash
pip install -r requirements.txt
```

---

### BƯỚC 2: Cấu hình MySQL

#### 2.1. Tạo file `.env` (nếu chưa có)

Tạo file `.env` trong thư mục `Cursor/` với nội dung:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=esp32_data
```

**Lưu ý:** 
- `MYSQL_PASSWORD=` để trống (XAMPP mặc định không có password)
- Nếu MySQL có password, thay bằng password của bạn

**Hoặc:** Double-click `SUA_FILE_ENV.bat` để tự động tạo file `.env`

---

#### 2.2. Start MySQL trong XAMPP

1. Mở **XAMPP Control Panel**
2. Click **[Start]** ở dòng **MySQL** (chuyển sang màu xanh)
3. Đợi MySQL khởi động xong

---

#### 2.3. Tạo bảng trong MySQL

1. **Mở phpMyAdmin:** http://localhost/phpmyadmin
2. **Chọn database** `esp32_data` (sidebar bên trái)
3. **Click tab SQL**
4. **Copy toàn bộ** nội dung file `database.sql` và **paste** vào
5. **Click Go**

**Kết quả:** Bảng `vehicle_records` đã được tạo ✅

---

### BƯỚC 3: Chạy Server

**Cách 1 (Dễ nhất):** Double-click file `CHAY_SERVER.bat`

**Cách 2:** Chạy thủ công:
```bash
python app.py
```

**Kết quả:** Server chạy tại http://localhost:5000

---

### BƯỚC 4: Truy cập

- **Trang chính:** http://localhost:5000
- **Đăng nhập:** http://localhost:5000/login
  - Username: `admin`
  - Password: `22138109`
- **API Docs:** http://localhost:5000/docs

---

## 📁 Cấu Trúc File

```
Cursor/
├── app.py                      # FastAPI server chính
├── config.py                   # Cấu hình MySQL
├── database.sql                # SQL tạo bảng
├── CHAY_SERVER.bat             # Script chạy server
├── SUA_FILE_ENV.bat            # Script sửa file .env
├── KIEM_TRA_MYSQL.bat          # Script kiểm tra MySQL
├── kiem_tra_config.py          # Script test kết nối
├── raspberry_pi_upload.py      # Script upload từ Pi
├── view_data.py                # Script xem dữ liệu
├── requirements.txt            # Python dependencies
├── templates/
│   └── index.html              # Giao diện web
└── uploads/                    # Thư mục lưu ảnh
```

---

## 📡 API Endpoints

### Upload dữ liệu từ thiết bị

```bash
POST /api/upload
Content-Type: application/json

{
  "license_plate": "29A-12345",
  "direction": "IN",  # hoặc "OUT"
  "vehicle_weight": 5.5,
  "device_id": "CAMERA_001",
  "notes": "Xe tải vào",
  "api_key": "raspberry_pi_key_123"
}
```

### Xem thống kê

```bash
GET /api/stats
Authorization: Bearer <token>
```

### Xem danh sách records

```bash
GET /api/records
Authorization: Bearer <token>
```

---

## 🔧 XỬ LÝ LỖI THƯỜNG GẶP

### ❌ Lỗi: Can't connect to MySQL server (10061)

**Nguyên nhân:** MySQL chưa được Start trong XAMPP

**Giải pháp:**
1. Mở XAMPP Control Panel
2. Click **[Start]** ở dòng MySQL
3. Đợi MySQL chuyển sang màu xanh
4. Chạy lại server: `python app.py`

---

### ❌ Lỗi: Access denied for user

**Nguyên nhân:** Password hoặc user MySQL sai

**Giải pháp:**
1. **Test password MySQL:**
   ```bash
   mysql -u root
   ```
   - Nếu vào được → Password trống → File `.env`: `MYSQL_PASSWORD=`
   - Nếu bị từ chối → MySQL có password → Thử password khác

2. **Sửa file `.env`:**
   ```env
   MYSQL_USER=root
   MYSQL_PASSWORD=  # Để trống hoặc password của bạn
   MYSQL_DATABASE=esp32_data
   ```

3. **Hoặc:** Double-click `SUA_FILE_ENV.bat` để tự động sửa

---

### ❌ Lỗi: Table 'vehicle_records' doesn't exist

**Nguyên nhân:** Chưa tạo bảng trong MySQL

**Giải pháp:**
1. Mở phpMyAdmin: http://localhost/phpmyadmin
2. Chọn database `esp32_data`
3. Tab SQL → Copy `database.sql` → Paste → Go

---

### ❌ Lỗi: Port 5000 đã được sử dụng

**Giải pháp:** Chạy trên port khác:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Sau đó truy cập: http://localhost:8000

---

### ❌ Lỗi: ModuleNotFoundError

**Giải pháp:**
```bash
pip install -r requirements.txt
```

---

## 🧪 CÔNG CỤ KIỂM TRA

### Kiểm tra MySQL đang chạy

Double-click: `KIEM_TRA_MYSQL.bat`

### Kiểm tra cấu hình

```bash
python kiem_tra_config.py
```

### Xem dữ liệu trong database

```bash
python view_data.py
```

---

## 📊 Cấu trúc bảng vehicle_records

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | INT | ID tự động |
| `license_plate` | VARCHAR(20) | Biển số xe |
| `direction` | VARCHAR(10) | **"IN"** (vào) hoặc **"OUT"** (ra) |
| `vehicle_weight` | DECIMAL(10,2) | Trọng lượng (tấn) |
| `capture_time` | DATETIME | Thời gian ghi nhận |
| `image_path` | VARCHAR(255) | Đường dẫn ảnh |
| `device_id` | VARCHAR(50) | ID thiết bị |
| `notes` | TEXT | Ghi chú |
| `created_at` | TIMESTAMP | Thời gian tạo (tự động) |

---

## 🛠️ Công Nghệ

- **Backend:** FastAPI (Python)
- **Database:** MySQL (XAMPP)
- **Frontend:** HTML, JavaScript, Bootstrap
- **Authentication:** JWT

---

## 📝 License

MIT

---

## 💡 Lưu Ý

- **MySQL phải Start trước** khi chạy Python server
- **Giữ XAMPP Control Panel mở** khi đang làm việc
- **File `.env`** sẽ override cấu hình trong `config.py`
- **Truy cập bằng `localhost:5000`** (KHÔNG phải `0.0.0.0:5000`)

---

**Nếu gặp vấn đề, chạy `KIEM_TRA_MYSQL.bat` và `python kiem_tra_config.py` để kiểm tra!**
