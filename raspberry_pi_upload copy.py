import requests
import base64
from datetime import datetime
import os
import sys
import cv2
import time

# ========== CẤU HÌNH ==========
# Thay đổi IP này thành IP của server của bạn
SERVER_URL = "http://192.168.101.36:5000"  
API_KEY = "raspberry_pi_key_123"
DEVICE_ID = "RASPBERRY_PI_001"

# ImgBB API Key
IMGBB_API_KEY = '42e11ba3563b75735c958d96aa6aea3f'
IMGBB_UPLOAD_URL = 'https://api.imgbb.com/1/upload'

# Endpoint upload file trực tiếp (dễ dùng hơn)
UPLOAD_ENDPOINT = f"{SERVER_URL}/api/upload-image"
# Endpoint upload base64 (backup)
UPLOAD_BASE64_ENDPOINT = f"{SERVER_URL}/api/upload"

# ========== FUNCTIONS ==========

def capture_image_with_camera(camera_index=0):
    try:
        
        print(f"📷 Đang mở camera index {camera_index}...")
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"⚠️  Không thể mở camera index {camera_index}.")
            print("   Thử kiểm tra:")
            print("   - Camera đã được cắm vào USB chưa?")
            print("   - Thử camera_index khác (1, 2, ...)")
            return None
        
        # Thiết lập độ phân giải 800x600
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
        
        # Đợi camera khởi động
        time.sleep(0.5)
        
        # Đọc frame
        ret, frame = cap.read()
        
        # Kiểm tra độ phân giải thực tế
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"   Độ phân giải: {actual_width}x{actual_height}")
        cap.release()
        
        if not ret or frame is None:
            print("⚠️  Không chụp được ảnh từ camera.")
            return None
        
        # Encode to JPEG với chất lượng tốt
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        _, buffer = cv2.imencode('.jpg', frame, encode_params)
        
        if buffer is None:
            print("⚠️  Không thể encode ảnh.")
            return None
        
        print(f"✅ Chụp ảnh thành công! Kích thước: {len(buffer.tobytes())} bytes")
        return buffer.tobytes()
        
    except ImportError:
        print("⚠️  OpenCV chưa cài đặt.")
        print("   Cài đặt: pip install opencv-python")
        print("   Hoặc trên Raspberry Pi: pip3 install opencv-python")
        return None
    except Exception as e:
        print(f"⚠️  Lỗi chụp ảnh: {e}")
        return None

def load_image_from_file(image_path):
    try:
        with open(image_path, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️  Không tìm thấy file: {image_path}")
        return None

def upload_image_to_imgbb(image_data):
    try:
        print("📤 Đang upload ảnh lên ImgBB...")
        
        # Convert image to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Prepare data for ImgBB API
        payload = {
            'key': IMGBB_API_KEY,
            'image': image_base64
        }
        
        # Upload to ImgBB
        response = requests.post(IMGBB_UPLOAD_URL, data=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                image_url = result['data']['url']
                print(f"✅ Upload lên ImgBB thành công!")
                print(f"   📸 URL: {image_url}")
                return image_url
            else:
                print(f"❌ ImgBB trả về lỗi: {result.get('error', {}).get('message', 'Unknown error')}")
                return None
        else:
            print(f"❌ Lỗi upload ImgBB: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Không thể kết nối đến ImgBB!")
        return None
    except Exception as e:
        print(f"❌ Lỗi upload ImgBB: {e}")
        return None

def detect_license_plate(image_data):
    print("🔍 Đang nhận dạng biển số...")
    print("⚠️  TODO: Tích hợp thư viện nhận dạng biển số")
    return "51A-TEST01"  # Placeholder

def upload_data_file(license_plate, image_data, vehicle_weight=None, direction="IN"):
    try:
        # Bước 1: Upload ảnh lên ImgBB
        image_url = upload_image_to_imgbb(image_data)
        if not image_url:
            print("⚠️  Không thể upload lên ImgBB, thử gửi file trực tiếp...")
            # Fallback: gửi file trực tiếp như cũ
            return upload_data_file_direct(license_plate, image_data, vehicle_weight, direction)
        
        # Bước 2: Gửi URL lên server qua endpoint /api/upload (JSON)
        # Vì có image_path (URL), nên dùng endpoint JSON thay vì multipart/form-data
        print(f"\n📤 Đang gửi dữ liệu lên server: {UPLOAD_BASE64_ENDPOINT}")
        
        data = {
            'license_plate': license_plate,
            'direction': direction,
            'device_id': DEVICE_ID,
            'api_key': API_KEY,
            'image_path': image_url,  # Gửi URL từ ImgBB
            'notes': f"Auto upload from Raspberry Pi - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        if vehicle_weight is not None:
            data['vehicle_weight'] = vehicle_weight
        
        # Gửi JSON request
        response = requests.post(UPLOAD_BASE64_ENDPOINT, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Thành công!")
            print(f"   🆔 Record ID: {result.get('id')}")
            print(f"   🚗 Biển số: {license_plate}")
            print(f"   ⚖️  Khối lượng: {vehicle_weight or 'N/A'} tấn")
            print(f"   📸 Ảnh URL: {result.get('image_path', image_url)}")
            print(f"   🕐 Thời gian: {result.get('capture_time')}")
            return True
        else:
            print(f"❌ Lỗi {response.status_code}:")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Không thể kết nối đến server!")
        print(f"   Kiểm tra: {SERVER_URL}")
        print(f"   Đảm bảo server đang chạy và IP đúng")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def upload_data_file_direct(license_plate, image_data, vehicle_weight=None, direction="IN"):
    try:
        print(f"\n📤 Đang gửi ảnh trực tiếp lên server: {UPLOAD_ENDPOINT}")
        
        # Prepare form data
        files = {
            'image': ('image.jpg', image_data, 'image/jpeg')
        }
        
        data = {
            'license_plate': license_plate,
            'direction': direction,
            'device_id': DEVICE_ID,
            'api_key': API_KEY,
            'notes': f"Auto upload from Raspberry Pi - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        if vehicle_weight is not None:
            data['vehicle_weight'] = str(vehicle_weight)
        
        response = requests.post(UPLOAD_ENDPOINT, files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Thành công!")
            print(f"   🆔 Record ID: {result.get('id')}")
            print(f"   🚗 Biển số: {license_plate}")
            print(f"   ⚖️  Khối lượng: {vehicle_weight or 'N/A'} tấn")
            print(f"   📸 Ảnh: {result.get('image_path', 'Đã lưu')}")
            print(f"   🕐 Thời gian: {result.get('capture_time')}")
            return True
        else:
            print(f"❌ Lỗi {response.status_code}:")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Không thể kết nối đến server!")
        print(f"   Kiểm tra: {SERVER_URL}")
        print(f"   Đảm bảo server đang chạy và IP đúng")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def upload_data_base64(license_plate, image_data=None, vehicle_weight=None, direction="IN"):
    try:
        # Bước 1: Upload ảnh lên ImgBB nếu có
        image_url = None
        if image_data:
            image_url = upload_image_to_imgbb(image_data)
            if not image_url:
                print("⚠️  Không thể upload lên ImgBB, thử gửi base64 trực tiếp...")
                # Fallback: gửi base64 như cũ
                return upload_data_base64_direct(license_plate, image_data, vehicle_weight, direction)
        
        # Bước 2: Gửi URL lên server
        print(f"\n📤 Đang gửi dữ liệu lên server (base64 endpoint): {UPLOAD_BASE64_ENDPOINT}")
        
        # Prepare data
        data = {
            "license_plate": license_plate,
            "direction": direction,  # "IN" hoặc "OUT"
            "vehicle_weight": vehicle_weight,
            "device_id": DEVICE_ID,
            "notes": f"Auto upload from Raspberry Pi - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "api_key": API_KEY
        }
        
        if image_url:
            data["image_path"] = image_url  # Gửi URL từ ImgBB
        
        response = requests.post(UPLOAD_BASE64_ENDPOINT, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Thành công!")
            print(f"   🆔 Record ID: {result.get('id')}")
            print(f"   🚗 Biển số: {license_plate}")
            print(f"   ⚖️  Khối lượng: {vehicle_weight or 'N/A'} tấn")
            print(f"   📸 Ảnh URL: {result.get('image_path', image_url)}")
            print(f"   🕐 Thời gian: {result.get('capture_time')}")
            return True
        else:
            print(f"❌ Lỗi {response.status_code}:")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Không thể kết nối đến server!")
        print(f"   Kiểm tra: {SERVER_URL}")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def upload_data_base64_direct(license_plate, image_data=None, vehicle_weight=None, direction="IN"):
    
    # Convert image to base64 nếu có
    image_base64 = None
    if image_data:
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        print(f"📷 Kích thước ảnh: {len(image_data)} bytes")
    
    # Prepare data
    data = {
        "license_plate": license_plate,
        "direction": direction,  # "IN" hoặc "OUT"
        "vehicle_weight": vehicle_weight,
        "device_id": DEVICE_ID,
        "notes": f"Auto upload from Raspberry Pi - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "api_key": API_KEY
    }
    
    if image_base64:
        data["image_base64"] = image_base64
    
    try:
        print(f"\n📤 Đang gửi lên server (base64): {UPLOAD_BASE64_ENDPOINT}")
        response = requests.post(UPLOAD_BASE64_ENDPOINT, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Thành công!")
            print(f"   🆔 Record ID: {result.get('id')}")
            print(f"   🚗 Biển số: {license_plate}")
            print(f"   ⚖️  Khối lượng: {vehicle_weight or 'N/A'} tấn")
            print(f"   📸 Ảnh: {'Có' if image_data else 'Không'}")
            print(f"   🕐 Thời gian: {result.get('capture_time')}")
            return True
        else:
            print(f"❌ Lỗi {response.status_code}:")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Không thể kết nối đến server!")
        print(f"   Kiểm tra: {SERVER_URL}")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def main(): 
    print("=" * 60)
    print("🍓 RASPBERRY PI - GỬI ẢNH TỪ USB CAMERA LÊN SERVER")
    print("=" * 60)
    print()
    
    # Kiểm tra kết nối server
    print(f"🔗 Kiểm tra kết nối server: {SERVER_URL}")
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server đang hoạt động!")
        else:
            print("⚠️  Server trả về lỗi, nhưng vẫn thử upload...")
    except:
        print("⚠️  Không thể kết nối server, nhưng vẫn thử upload...")
    
    print()
    
    # Chụp ảnh từ camera
    print("📸 Bước 1: Chụp ảnh từ USB camera...")
    image_data = None
    
    # Thử camera index 0, 1, 2...
    for camera_idx in range(3):
        image_data = capture_image_with_camera(camera_index=camera_idx)
        if image_data:
            break
    
    if not image_data:
        print("⚠️  Không có ảnh từ camera, thử dùng file test...")
        # Có thể dùng ảnh từ file thay thế
        test_image_path = "test_image.jpg"
        if os.path.exists(test_image_path):
            image_data = load_image_from_file(test_image_path)
            print(f"✅ Đã tải ảnh từ file: {test_image_path}")
    
    if not image_data:
        print("❌ Không có ảnh để upload!")
        print("   Vui lòng:")
        print("   - Kiểm tra USB camera đã được cắm")
        print("   - Hoặc đặt file test_image.jpg trong thư mục hiện tại")
        return
    
    # Nhận dạng biển số
    print("\n🔍 Bước 2: Nhận dạng biển số...")
    license_plate = detect_license_plate(image_data)
    print(f"   Biển số: {license_plate}")
    
    # Giả định khối lượng (hoặc đọc từ cảm biến)
    vehicle_weight = 3.5  # TODO: Đọc từ cảm biến thực tế
    
    # Hỏi hướng xe (hoặc tự động phát hiện)
    direction = "IN"  # Mặc định là vào
    # TODO: Có thể thêm logic tự động phát hiện hướng
    
    # Gửi lên server - Ưu tiên dùng upload file trực tiếp
    print("\n📤 Bước 3: Gửi ảnh lên server...")
    success = upload_data_file(license_plate, image_data, vehicle_weight, direction)
    
    # Nếu upload file thất bại, thử base64
    if not success:
        print("\n⚠️  Upload file thất bại, thử phương pháp base64...")
        success = upload_data_base64(license_plate, image_data, vehicle_weight, direction)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ HOÀN TẤT! Dữ liệu đã được lưu vào server.")
        print(f"   Xem tại: {SERVER_URL}/dashboard")
    else:
        print("❌ THẤT BẠI! Kiểm tra:")
        print(f"   - Server đang chạy: {SERVER_URL}")
        print(f"   - API key đúng: {API_KEY}")
        print(f"   - Kết nối mạng giữa Raspberry Pi và server")
    print("=" * 60)

if __name__ == "__main__":
    main()

