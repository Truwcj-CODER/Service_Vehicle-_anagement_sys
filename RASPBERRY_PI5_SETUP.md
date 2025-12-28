# 🍓 Hướng Dẫn Cài Đặt Trên Raspberry Pi 5

## 📋 Yêu Cầu

- Raspberry Pi 5 (ARM64)
- USB Camera
- Kết nối mạng (WiFi/Ethernet)
- Python 3.9+ (thường đã có sẵn trên Pi OS)

---

## 🔧 Bước 1: Cài Đặt System Dependencies

```bash
# Cập nhật hệ thống
sudo apt-get update
sudo apt-get upgrade -y

# Cài đặt Python và các thư viện cơ bản
sudo apt-get install -y python3-pip python3-dev python3-venv
sudo apt-get install -y libopencv-dev python3-opencv
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
sudo apt-get install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
```

---

## 📦 Bước 2: Cài Đặt Python Packages

### Tạo virtual environment (khuyến nghị):

```bash
cd ~/your-project-folder
python3 -m venv venv
source venv/bin/activate
```

### Cài đặt packages cơ bản:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Cài đặt OCR (chọn 1 trong 2):

#### Option 1: PaddleOCR (Khuyến nghị - nhanh và chính xác)

```bash
# Trên Raspberry Pi 5, có thể cần cài từ source
pip install paddlepaddle paddleocr

# Nếu lỗi, thử:
pip install paddlepaddle==2.5.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install paddleocr -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Lưu ý:** PaddleOCR trên Pi 5 có thể mất 10-30 phút để cài đặt lần đầu.

#### Option 2: EasyOCR (Dễ cài hơn)

```bash
pip install easyocr
```

**Lưu ý:** Lần đầu chạy sẽ tự động download model (~500MB), mất vài phút.

---

## 🔌 Bước 3: Kiểm Tra Camera

```bash
# Kiểm tra camera có được nhận diện không
lsusb

# Xem device camera
v4l2-ctl --list-devices

# Test camera
raspistill -o test.jpg
# Hoặc
ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test.jpg
```

---

## ⚙️ Bước 4: Cấu Hình Script

Mở file `raspberry_pi_upload.py` và sửa:

```python
# Dòng 29: IP server của bạn
SERVER_URL = "http://192.168.1.XXX:5000"  # ← SỬA IP NÀY

# Dòng 30: API key (phải khớp với server)
API_KEY = "raspberry_pi_key_123"

# Dòng 31: ID thiết bị
DEVICE_ID = "RASPBERRY_PI_001"

# Dòng 43: Cổng Serial (ESP32)
SERIAL_PORT = "/dev/ttyUSB0"  # Hoặc /dev/ttyACM0
```

**Tìm IP server:**
- Trên Windows: `ipconfig` → Tìm `IPv4 Address`
- Trên Linux/Mac: `ifconfig` hoặc `ip addr`

---

## 🚀 Bước 5: Chạy Script

```bash
# Kích hoạt virtual environment (nếu dùng)
source venv/bin/activate

# Chạy script
python3 raspberry_pi_upload.py
```

---

## 🐛 Xử Lý Lỗi Thường Gặp

### Lỗi: "No module named 'cv2'"

```bash
sudo apt-get install python3-opencv
# Hoặc
pip install opencv-python-headless
```

### Lỗi: "Permission denied" khi truy cập camera

```bash
# Thêm user vào group video
sudo usermod -a -G video $USER
# Logout và login lại
```

### Lỗi: "Permission denied" khi truy cập Serial

```bash
# Thêm user vào group dialout
sudo usermod -a -G dialout $USER
# Logout và login lại
```

### Lỗi: PaddleOCR không cài được

```bash
# Dùng EasyOCR thay thế
pip install easyocr
```

### Lỗi: "Out of memory" khi chạy OCR

```bash
# Tăng swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Đổi CONF_SWAPSIZE=100 thành 2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## 📊 Kiểm Tra Hiệu Suất

### Xem CPU và RAM:

```bash
htop
# Hoặc
top
```

### Xem nhiệt độ:

```bash
vcgencmd measure_temp
```

---

## 🔄 Chạy Tự Động Khi Khởi Động

### Cách 1: Dùng systemd (Khuyến nghị)

Tạo file `/etc/systemd/system/license-plate.service`:

```ini
[Unit]
Description=License Plate Recognition Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/your-project-folder
Environment="PATH=/home/pi/your-project-folder/venv/bin"
ExecStart=/home/pi/your-project-folder/venv/bin/python3 /home/pi/your-project-folder/raspberry_pi_upload.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Kích hoạt:

```bash
sudo systemctl daemon-reload
sudo systemctl enable license-plate.service
sudo systemctl start license-plate.service

# Xem log
sudo journalctl -u license-plate.service -f
```

### Cách 2: Dùng crontab

```bash
crontab -e
# Thêm dòng:
@reboot cd /home/pi/your-project-folder && /home/pi/your-project-folder/venv/bin/python3 /home/pi/your-project-folder/raspberry_pi_upload.py
```

---

## ✅ Checklist Trước Khi Chạy

- [ ] Đã cài đặt system dependencies
- [ ] Đã cài đặt Python packages (requirements.txt)
- [ ] Đã cài đặt ít nhất 1 OCR (PaddleOCR hoặc EasyOCR)
- [ ] Đã kiểm tra camera hoạt động
- [ ] Đã cấu hình SERVER_URL, API_KEY trong script
- [ ] Đã kiểm tra kết nối mạng
- [ ] Server đang chạy và có thể truy cập được

---

## 💡 Tips

1. **Dùng EasyOCR nếu PaddleOCR quá nặng:** EasyOCR dễ cài hơn và nhẹ hơn trên Pi 5
2. **Tắt GUI để tiết kiệm RAM:** `sudo systemctl set-default multi-user.target`
3. **Dùng USB 3.0 cho camera:** Pi 5 có USB 3.0, nhanh hơn
4. **Monitor nhiệt độ:** Pi 5 có thể nóng, cần tản nhiệt tốt

---

## 📞 Hỗ Trợ

Nếu gặp vấn đề, kiểm tra:
- Log output của script
- System log: `sudo journalctl -xe`
- Camera: `v4l2-ctl --all`
- Network: `ping SERVER_IP`

