# Hướng Dẫn Cài Đặt Docker trên Windows

## Bước 1: Tải Docker Desktop

1. Truy cập: https://www.docker.com/products/docker-desktop/
2. Tải **Docker Desktop for Windows**
3. Chạy file installer và làm theo hướng dẫn

## Bước 2: Khởi động Docker Desktop

1. Sau khi cài đặt, mở **Docker Desktop** từ Start Menu
2. Đợi Docker khởi động hoàn toàn (icon Docker ở system tray sẽ không còn loading)
3. Đảm bảo Docker đang chạy (icon Docker màu xanh)

## Bước 3: Kiểm tra cài đặt

Mở PowerShell và chạy:

```powershell
# Kiểm tra Docker
docker --version

# Kiểm tra Docker Compose (có thể là "docker compose" hoặc "docker-compose")
docker compose version
# hoặc
docker-compose --version
```

## Bước 4: Chạy ứng dụng

Sau khi Docker đã cài đặt và chạy, bạn có thể:

### Cách 1: Dùng lệnh mới (Docker Desktop mới)
```powershell
docker compose up -d
```

### Cách 2: Dùng lệnh cũ (nếu có docker-compose riêng)
```powershell
docker-compose up -d
```

### Hoặc dùng script PowerShell
```powershell
.\docker-start.ps1
```

## Lưu ý quan trọng

1. **WSL 2**: Docker Desktop yêu cầu WSL 2 trên Windows. Nếu chưa có, Docker Desktop sẽ hướng dẫn cài đặt.

2. **Hyper-V**: Một số phiên bản Windows cần bật Hyper-V (thường tự động khi cài Docker Desktop).

3. **Khởi động lại**: Sau khi cài Docker Desktop, có thể cần khởi động lại máy.

## Troubleshooting

### Lỗi "WSL 2 installation is incomplete"
- Cài đặt WSL 2: https://docs.microsoft.com/en-us/windows/wsl/install
- Hoặc chạy trong PowerShell (Admin):
  ```powershell
  wsl --install
  ```

### Docker Desktop không khởi động
- Kiểm tra Windows Update
- Đảm bảo Virtualization đã bật trong BIOS
- Thử chạy Docker Desktop với quyền Administrator

### Port đã được sử dụng
- Kiểm tra xem port 5000 hoặc 3306 có đang được dùng không
- Sửa port trong `docker-compose.yaml` nếu cần


