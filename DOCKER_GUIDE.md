# Hướng Dẫn Chạy Ứng Dụng với Docker Compose

## Yêu Cầu
- Docker Desktop (Windows/Mac) hoặc Docker Engine (Linux)
- Docker Compose (thường đi kèm với Docker Desktop)

## ⚠️ Cài Đặt Docker (Nếu chưa có)

Nếu gặp lỗi "docker-compose is not recognized", bạn cần cài Docker Desktop trước:
- **Xem hướng dẫn chi tiết**: `DOCKER_INSTALL_GUIDE.md`
- **Tải Docker Desktop**: https://www.docker.com/products/docker-desktop/

## Cách Chạy

### Cách 1: Dùng Script PowerShell (Khuyến nghị - Windows)
```powershell
.\docker-start.ps1
```

### Cách 2: Dùng Lệnh Trực Tiếp

**Lưu ý**: Docker Desktop mới dùng `docker compose` (có khoảng trắng), cũ dùng `docker-compose` (có dấu gạch ngang)

#### 1. Khởi động tất cả services
```powershell
# Thử lệnh mới trước (Docker Desktop mới)
docker compose up -d

# Hoặc lệnh cũ (nếu lệnh trên không hoạt động)
docker-compose up -d
```

#### 2. Xem logs
```powershell
# Xem logs của tất cả services
docker compose logs -f
# hoặc
docker-compose logs -f

# Xem logs của service cụ thể
docker compose logs -f app
docker compose logs -f mysql
```

#### 3. Dừng services
```powershell
docker compose down
# hoặc
docker-compose down
```

#### 4. Dừng và xóa volumes (xóa dữ liệu database)
```powershell
docker compose down -v
# hoặc
docker-compose down -v
```

#### 5. Rebuild lại image khi có thay đổi code
```powershell
docker compose up -d --build
# hoặc
docker-compose up -d --build
```

## Truy Cập Ứng Dụng

- **Web Interface**: http://localhost:5000
- **Login Page**: http://localhost:5000/login
- **API Docs**: http://localhost:5000/docs (Swagger UI)
- **MySQL**: localhost:3306
  - User: `app_user`
  - Password: `app_password`
  - Database: `esp32_data`

## Cấu Hình

### Thay đổi mật khẩu MySQL
Sửa trong file `docker-compose.yaml`:
```yaml
environment:
  MYSQL_ROOT_PASSWORD: your_new_password
  MYSQL_PASSWORD: your_new_password
```

### Thay đổi biến môi trường
Sửa trong file `docker-compose.yaml` phần `app` service, hoặc tạo file `.env` và tham chiếu trong docker-compose.yaml.

## Kiểm Tra Trạng Thái

```powershell
# Xem trạng thái các containers
docker compose ps
# hoặc
docker-compose ps

# Kiểm tra health
docker compose ps
```

## Troubleshooting

### Docker chưa được cài đặt
- Xem `DOCKER_INSTALL_GUIDE.md` để cài đặt Docker Desktop
- Đảm bảo Docker Desktop đang chạy (icon Docker ở system tray)

### Database không kết nối được
1. Kiểm tra MySQL đã sẵn sàng:
   ```powershell
   docker compose logs mysql
   # hoặc
   docker-compose logs mysql
   ```
2. Đợi MySQL khởi động hoàn toàn (có thể mất 30-60 giây)

### Port đã được sử dụng
Nếu port 5000 hoặc 3306 đã được sử dụng, sửa trong `docker-compose.yaml`:
```yaml
ports:
  - "5001:5000"  # Thay đổi port bên trái
```

### Xóa và tạo lại từ đầu
```powershell
docker compose down -v
docker compose up -d --build
# hoặc
docker-compose down -v
docker-compose up -d --build
```

