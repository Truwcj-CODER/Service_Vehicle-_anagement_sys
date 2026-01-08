import requests
import base64
from datetime import datetime
import os
import sys
import cv2
import time
import serial
import threading
import numpy as np
import re
import random

# Thử import PaddleOCR (nếu có) - ƯU TIÊN CAO NHẤT
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

# Thử import EasyOCR (nếu có)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# ========== CẤU HÌNH ==========
# Thay đổi IP này thành IP của server của bạn
SERVER_URL = "http://10.25.84.229:5000"  
API_KEY = "raspberry_pi_key_123"
DEVICE_ID = "RASPBERRY_PI_001"

# ImgBB API Key
IMGBB_API_KEY = '42e11ba3563b75735c958d96aa6aea3f'
IMGBB_UPLOAD_URL = 'https://api.imgbb.com/1/upload'

# Endpoint upload file trực tiếp (dễ dùng hơn)
UPLOAD_ENDPOINT = f"{SERVER_URL}/api/upload-image"
# Endpoint upload base64 (backup)
UPLOAD_BASE64_ENDPOINT = f"{SERVER_URL}/api/upload"

# ========== CẤU HÌNH CÂN & CAMERA ==========
SERIAL_PORT = "/dev/ttyUSB0"  # Cổng ESP32 (trên Windows: "COM3", "COM4", ...)
BAUD_RATE = 9600
MIN_WEIGHT_KG = 0.03  # Trọng lượng tối thiểu để kích hoạt (30g)
SCAN_TIMEOUT = 10  # Thời gian chờ tối đa để nhận dạng biển số (giây)

# ========== CẤU HÌNH DTK LPR SDK ==========
# Lưu ý: Cần cài đặt DTK LPR SDK và Python bindings trước
# Tải từ: https://www.dtksoft.com/lprsdk
DTK_LPR_ENABLED = False  # Đặt True sau khi cài đặt SDK
DTK_LPR_COUNTRIES = "VN,US,DE,NL,DK,PL"  # Các quốc gia hỗ trợ
DTK_LPR_MIN_PLATE_WIDTH = 80
DTK_LPR_MAX_PLATE_WIDTH = 300

# ========== BIẾN TOÀN CỤC ==========
latest_frame = None
frame_lock = threading.Lock()
scan_trigger = False
current_weight = 0.0
scan_start_time = 0
is_object_on_scale = False
last_trigger_time = 0  # Track thời gian lần trigger cuối cùng
lpr_engine = None

# ========== FUNCTIONS ==========

def get_random_weight():
    """
    Generate giá trị cân ảo từ 3.0 đến 5.0 kg (số xấu không đẹp)
    """
    # Generate số với 3 chữ số thập phân để tránh số "đẹp" như 3.5, 4.0, etc.
    return round(random.uniform(3.0, 5.0), 3)

def capture_image_with_camera(camera_index=0, cap=None):
    """
    Chụp ảnh từ camera
    Nếu cap được truyền vào, sẽ dùng camera đó (không release)
    Nếu không, sẽ mở camera mới và release sau khi chụp
    """
    try:
        should_release = False
        if cap is None:
            print(f"📷 Đang mở camera index {camera_index}...")
            cap = cv2.VideoCapture(camera_index)
            should_release = True
            
            if not cap.isOpened():
                print(f"⚠️  Không thể mở camera index {camera_index}.")
                print("   Thử kiểm tra:")
                print("   - Camera đã được cắm vào USB chưa?")
                print("   - Thử camera_index khác (1, 2, ...)")
                return None, None
            
            # Thiết lập độ phân giải
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Đọc frame
        ret, frame = cap.read()
        
        if not ret or frame is None:
            if should_release:
                cap.release()
            print("⚠️  Không chụp được ảnh từ camera.")
            return None, None
        
        # Encode to JPEG với chất lượng tốt
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        _, buffer = cv2.imencode('.jpg', frame, encode_params)
        
        if buffer is None:
            if should_release:
                cap.release()
            print("⚠️  Không thể encode ảnh.")
            return None, None
        
        image_data = buffer.tobytes()
        if should_release:
            cap.release()
        
        return image_data, frame
        
    except ImportError:
        print("⚠️  OpenCV chưa cài đặt.")
        print("   Cài đặt: pip install opencv-python")
        print("   Hoặc trên Raspberry Pi: pip3 install opencv-python")
        return None, None
    except Exception as e:
        print(f"⚠️  Lỗi chụp ảnh: {e}")
        return None, None

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

# ========== OCR FUNCTIONS ==========

def is_vietnam_license_plate(text):
    """
    Kiểm tra xem text có phải biển số Việt Nam không
    Format: XX-XXXXX hoặc XXX-XXXXX (có thể có dấu chấm, khoảng trắng)
    Ví dụ: 60C-55555, 30A-12345, 60C 555.55, T61 679.60
    """
    text_upper = text.upper().strip()
    text_clean = re.sub(r'[\s\.\-]', '', text_upper)
    
    if len(text_clean) < 6 or len(text_clean) > 10:
        return False
    
    has_letter = any(c.isalpha() for c in text_clean)
    has_digit = any(c.isdigit() for c in text_clean)
    
    if not (has_letter and has_digit):
        return False
    
    pattern1 = re.match(r'^[A-Z]?\d{2,3}[A-Z]{0,2}\d{4,6}$', text_clean)
    pattern2 = re.match(r'^[A-Z]{2,3}\d{4,7}$', text_clean)
    
    parts = re.split(r'[\s\.\-]+', text_upper)
    if len(parts) == 2:
        part1 = re.sub(r'[\s\.\-]', '', parts[0].strip())
        part2 = re.sub(r'[\s\.\-]', '', parts[1].strip())
        part1_match = (re.match(r'^[A-Z]?\d{2,3}[A-Z]{0,2}$', part1) or 
                       re.match(r'^\d{2,3}[A-Z]{1,2}$', part1))
        part2_match = re.match(r'^\d{3,6}$', part2)
        if part1_match and part2_match:
            return True
    
    if re.match(r'^[A-Z]\d{2,3}\d{4,6}$', text_clean):
        return True
    
    return bool(pattern1 or pattern2)

def detect_license_plate_with_paddleocr(img):
    """
    Nhận dạng biển số bằng PaddleOCR (VIP - ưu tiên cao nhất)
    Version nâng cấp với logic hoàn chỉnh từ test_image.py
    """
    if not PADDLEOCR_AVAILABLE:
        return None
    
    try:
        ocr = PaddleOCR(use_textline_orientation=True, lang='vi')
        predict_result = ocr.predict(img)
        
        if isinstance(predict_result, list) and len(predict_result) > 0:
            result_obj = predict_result[0]
        else:
            result_obj = predict_result
        
        if hasattr(result_obj, 'rec_texts'):
            rec_texts = result_obj.rec_texts
            rec_scores = result_obj.rec_scores
            rec_polys = result_obj.rec_polys
        elif isinstance(result_obj, dict):
            rec_texts = result_obj.get('rec_texts', [])
            rec_scores = result_obj.get('rec_scores', [])
            rec_polys = result_obj.get('rec_polys', [])
        else:
            print("  ⚠️  Không parse được dữ liệu từ PaddleOCR")
            return None
        
        print(f"  📊 PaddleOCR phát hiện {len(rec_texts)} text(s):")
        
        # Lọc và tìm biển số
        license_plate_candidates = []
        h, w = img.shape[:2]
        
        for i, (poly, text, score) in enumerate(zip(rec_polys, rec_texts, rec_scores)):
            text_clean = text.strip().upper()
            print(f"    [{i}] '{text_clean}' (score: {score:.2%})", end="")
            
            # Bỏ qua text quá ngắn hoặc quá dài
            # Nhưng cho phép text 2 ký tự nếu nó là prefix/suffix (sẽ check sau)
            if len(text_clean) == 0 or len(text_clean) > 20:
                print(" → Loại (độ dài)")
                continue
            
            # Bỏ qua text chỉ có chữ dài (như "THACO", "FORLAND")
            if text_clean.isalpha() and len(text_clean) > 5:
                print(" → Loại (toàn chữ dài)")
                continue
            
            # Kiểm tra format biển số Việt Nam
            if is_vietnam_license_plate(text_clean):
                # Tính vị trí Y trung bình của bbox
                y_center = sum(pt[1] for pt in poly) / len(poly)
                position_score = 1.0 if y_center > h * 0.5 else 0.5
                
                license_plate_candidates.append({
                    'text': text_clean,
                    'confidence': score,
                    'position_score': position_score,
                    'total_score': score * position_score
                })
                print(f" ✅ Match biển số! (score tổng: {score * position_score:.2%})")
            else:
                print(" → Không match format (nhưng có thể là prefix/suffix)")
        
        if license_plate_candidates:
            # Chọn candidate có điểm cao nhất
            best = max(license_plate_candidates, key=lambda x: x['total_score'])
            print(f"  ✅ Chọn: {best['text']}")
            return best['text']
        
        print(f"  ℹ️  Không tìm text match biển số, thử ghép...")
        
        # Thử ghép các text gần nhau lại
        plate_prefixes = []
        plate_suffixes = []
        
        for poly, text, score in zip(rec_polys, rec_texts, rec_scores):
            text_clean = text.strip().upper()
            
            if len(text_clean) == 0:
                continue
            
            # Clean text: loại bỏ dấu gạch ngang, khoảng trắng để check pattern
            text_for_pattern = re.sub(r'[\s\-]', '', text_clean)
            
            # Đơn giản hóa logic:
            # Prefix: text có chữ + có số + độ dài 2-5 (ví dụ: 62-M1, 60C, 30A, T61)
            has_letter = any(c.isalpha() for c in text_for_pattern)
            has_digit = any(c.isdigit() for c in text_for_pattern)
            
            if has_letter and has_digit and 2 <= len(text_for_pattern) <= 5:
                # Đây là prefix
                y_center = sum(pt[1] for pt in poly) / len(poly)
                plate_prefixes.append((poly, text_clean, score, y_center))
                print(f"  📌 Prefix candidate: '{text_clean}' (clean: '{text_for_pattern}')")
            # Phần sau: chỉ có số (ví dụ: 1679, 939, 939.98, 555.55)
            elif has_digit and not has_letter and 2 <= len(text_for_pattern) <= 6:
                y_center = sum(pt[1] for pt in poly) / len(poly)
                plate_suffixes.append((poly, text_clean, score, y_center))
                print(f"  📌 Suffix candidate: '{text_clean}' (clean: '{text_for_pattern}')")
        
        # Thử ghép prefix và suffix gần nhau
        print(f"  🔍 Bắt đầu ghép: {len(plate_prefixes)} prefixes × {len(plate_suffixes)} suffixes")
        try:
            for (poly1, text1, conf1, y1) in plate_prefixes:
                for (poly2, text2, conf2, y2) in plate_suffixes:
                    combined = f"{text1} {text2}".upper().strip()
                    # Clean combined text trước khi check (loại tất cả ký tự đặc biệt)
                    combined_clean = re.sub(r'[\s\-\.\·]', '', combined)
                    print(f"  🔄 Thử ghép: '{text1}' + '{text2}' → '{combined_clean}'")
                    if is_vietnam_license_plate(combined_clean):
                        print(f"  ✅ Ghép thành công: '{combined}'")
                        return combined
                    else:
                        print(f"     → Không match format")
        except Exception as e:
            print(f"  ❌ Lỗi ghép: {e}")
            import traceback
            traceback.print_exc()
        
        # Nếu không ghép được, thử tất cả các cặp
        for (poly1, text1, conf1) in [(p, t, s) for p, t, s, y in plate_prefixes]:
            for (poly2, text2, conf2) in [(p, t, s) for p, t, s, y in plate_suffixes]:
                combined = f"{text1} {text2}".upper().strip()
                # Clean combined text trước khi check (loại tất cả ký tự đặc biệt)
                combined_clean = re.sub(r'[\s\-\.\·]', '', combined)
                if is_vietnam_license_plate(combined_clean):
                    print(f"  ✅ Ghép (all pairs): '{text1}' + '{text2}' = '{combined}'")
                    return combined
        
        print(f"  ❌ Không ghép được")
        return None
    except Exception as e:
        print(f"  ❌ Lỗi PaddleOCR: {e}")
        import traceback
        traceback.print_exc()
        return None

def detect_license_plate_with_easyocr(img):
    """
    Nhận dạng biển số bằng EasyOCR (fallback)
    Version nâng cấp với logic hoàn chỉnh từ test_image.py
    """
    if not EASYOCR_AVAILABLE:
        return None
    
    try:
        reader = easyocr.Reader(['en', 'vi'], gpu=False)
        results = reader.readtext(img)
        
        if not results:
            print("  ⚠️  EasyOCR không phát hiện text nào")
            return None
        
        print(f"  📊 EasyOCR phát hiện {len(results)} text(s):")
        
        # Lọc và tìm biển số 
        license_plate_candidates = []
        h, w = img.shape[:2]
        
        for i, (bbox, text, confidence) in enumerate(results):
            text_clean = text.strip().upper()
            print(f"    [{i}] '{text_clean}' (conf: {confidence:.2%})", end="")
            
            # Bỏ qua text quá ngắn hoặc quá dài
            # Nhưng cho phép text 2 ký tự nếu nó là prefix/suffix (sẽ check sau)
            if len(text_clean) == 0 or len(text_clean) > 20:
                print(" → Loại (độ dài)")
                continue
            
            # Bỏ qua text chỉ có chữ dài (như "THACO", "FORLAND")
            if text_clean.isalpha() and len(text_clean) > 5:
                print(" → Loại (toàn chữ dài)")
                continue
            
            # Kiểm tra format biển số Việt Nam
            if is_vietnam_license_plate(text_clean):
                # Tính vị trí Y trung bình của bbox
                y_center = sum(pt[1] for pt in bbox) / len(bbox)
                position_score = 1.0 if y_center > h * 0.5 else 0.5
                
                license_plate_candidates.append({
                    'text': text_clean,
                    'confidence': confidence,
                    'position_score': position_score,
                    'total_score': confidence * position_score
                })
                print(f" ✅ Match biển số! (score tổng: {confidence * position_score:.2%})")
            else:
                print(" → Không match format (nhưng có thể là prefix/suffix)")
        
        if license_plate_candidates:
            # Chọn candidate có điểm cao nhất
            best = max(license_plate_candidates, key=lambda x: x['total_score'])
            print(f"  ✅ Chọn: {best['text']}")
            return best['text']
        
        print(f"  ℹ️  Không tìm text match biển số, thử ghép...")
        
        # Thử ghép các text gần nhau lại
        plate_prefixes = []
        plate_suffixes = []
        
        for (bbox, text, conf) in results:
            text_clean = text.strip().upper()
            
            if len(text_clean) == 0:
                continue
            
            # Clean text: loại bỏ dấu gạch ngang, khoảng trắng để check pattern
            text_for_pattern = re.sub(r'[\s\-]', '', text_clean)
            
            # Đơn giản hóa logic:
            # Prefix: text có chữ + có số + độ dài 2-5 (ví dụ: 62-M1, 60C, 30A, T61)
            has_letter = any(c.isalpha() for c in text_for_pattern)
            has_digit = any(c.isdigit() for c in text_for_pattern)
            
            if has_letter and has_digit and 2 <= len(text_for_pattern) <= 5:
                # Đây là prefix
                y_center = sum(pt[1] for pt in bbox) / len(bbox)
                plate_prefixes.append((bbox, text_clean, conf, y_center))
                print(f"  📌 Prefix candidate: '{text_clean}' (clean: '{text_for_pattern}')")
            # Phần sau: chỉ có số (ví dụ: 1679, 939, 939.98, 555.55)
            elif has_digit and not has_letter and 2 <= len(text_for_pattern) <= 6:
                y_center = sum(pt[1] for pt in bbox) / len(bbox)
                plate_suffixes.append((bbox, text_clean, conf, y_center))
                print(f"  📌 Suffix candidate: '{text_clean}' (clean: '{text_for_pattern}')")
        
        # Thử ghép prefix và suffix gần nhau
        print(f"  🔍 Bắt đầu ghép: {len(plate_prefixes)} prefixes × {len(plate_suffixes)} suffixes")
        try:
            for (bbox1, text1, conf1, y1) in plate_prefixes:
                for (bbox2, text2, conf2, y2) in plate_suffixes:
                    combined = f"{text1} {text2}".upper().strip()
                    # Clean combined text trước khi check (loại tất cả ký tự đặc biệt)
                    combined_clean = re.sub(r'[\s\-\.\·]', '', combined)
                    print(f"  🔄 Thử ghép: '{text1}' + '{text2}' → '{combined_clean}'")
                    if is_vietnam_license_plate(combined_clean):
                        print(f"  ✅ Ghép thành công: '{combined}'")
                        return combined
                    else:
                        print(f"     → Không match format")
        except Exception as e:
            print(f"  ❌ Lỗi ghép: {e}")
            import traceback
            traceback.print_exc()
        
        # Nếu không ghép được, thử tất cả các cặp
        for (bbox1, text1, conf1) in [(b, t, c) for b, t, c, y in plate_prefixes]:
            for (bbox2, text2, conf2) in [(b, t, c) for b, t, c, y in plate_suffixes]:
                combined = f"{text1} {text2}".upper().strip()
                # Clean combined text trước khi check (loại tất cả ký tự đặc biệt)
                combined_clean = re.sub(r'[\s\-\.\·]', '', combined)
                if is_vietnam_license_plate(combined_clean):
                    print(f"  ✅ Ghép (all pairs): '{text1}' + '{text2}' = '{combined}'")
                    return combined
        
        print(f"  ❌ Không ghép được")
        return None
    except Exception as e:
        print(f"  ❌ Lỗi EasyOCR: {e}")
        import traceback
        traceback.print_exc()
        return None

# ========== DTK LPR SDK INTEGRATION ==========

def init_dtk_lpr():
    """
    Khởi tạo DTK LPR Engine
    Lưu ý: Cần cài đặt DTK LPR SDK và Python bindings trước
    """
    global lpr_engine
    
    if not DTK_LPR_ENABLED:
        print("⚠️  DTK LPR SDK chưa được kích hoạt")
        print("   Để sử dụng:")
        print("   1. Tải DTK LPR SDK từ: https://www.dtksoft.com/lprsdk")
        print("   2. Cài đặt Python bindings")
        print("   3. Đặt DTK_LPR_ENABLED = True trong config")
        return False
    
    try:
        # Import DTK LPR SDK (cần cài đặt trước)
        # Tên module có thể khác tùy vào cách cài đặt (dtklpr, DTKLPR, etc.)
        try:
            from dtklpr import LPREngine, LPRParams
        except ImportError:
            try:
                from DTKLPR import LPREngine, LPRParams
            except ImportError:
                raise ImportError("Không tìm thấy module DTK LPR SDK")
        
        # Tạo LPR Parameters (tương tự như C#)
        params = LPRParams()
        params.Countries = DTK_LPR_COUNTRIES
        params.MinPlateWidth = DTK_LPR_MIN_PLATE_WIDTH
        params.MaxPlateWidth = DTK_LPR_MAX_PLATE_WIDTH
        
        # Khởi tạo engine với callback (True = enable callback, on_license_plate_detected)
        lpr_engine = LPREngine(params, True, on_license_plate_detected)
        
        print("✅ DTK LPR Engine đã được khởi tạo")
        print(f"   Countries: {DTK_LPR_COUNTRIES}")
        print(f"   Plate width: {DTK_LPR_MIN_PLATE_WIDTH}-{DTK_LPR_MAX_PLATE_WIDTH}px")
        return True
    except ImportError as e:
        print("❌ Không tìm thấy DTK LPR SDK Python bindings")
        print(f"   Lỗi: {e}")
        print("   Vui lòng cài đặt theo hướng dẫn từ: https://www.dtksoft.com/lprsdk")
        return False
    except Exception as e:
        print(f"❌ Lỗi khởi tạo DTK LPR: {e}")
        return False

def on_license_plate_detected(engine, plate):
    """
    Callback khi DTK LPR phát hiện biển số
    """
    global scan_trigger
    
    plate_text = plate.Text
    country = plate.CountryCode
    confidence = plate.Confidence
    
    print(f"🎯 PHÁT HIỆN BIỂN SỐ: {plate_text}")
    print(f"   Quốc gia: {country}, Độ tin cậy: {confidence:.2f}%")
    
    # Xử lý upload lên server
    if latest_frame is not None:
        with frame_lock:
            frame_copy = latest_frame.copy()
        
        # Encode frame thành JPEG
        _, buffer = cv2.imencode('.jpg', frame_copy)
        image_data = buffer.tobytes()
        
        # Upload lên server
        upload_data_file(plate_text, image_data, current_weight, "IN")
    
    # Dừng quét
    scan_trigger = False
    plate.Dispose()

def detect_license_plate_from_image(image_data, image_path=None):
    """
    Nhận dạng biển số từ ảnh tĩnh
    Thứ tự ưu tiên: PaddleOCR → EasyOCR → DTK LPR SDK
    
    Args:
        image_data: bytes của ảnh (JPEG/PNG)
        image_path: (optional) đường dẫn file ảnh
    
    Returns:
        str: Biển số đã nhận dạng, hoặc None nếu không tìm thấy
    """
    # Chuyển đổi image_data thành numpy array
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            print("❌ Không thể decode ảnh")
            return None
    except Exception as e:
        print(f"❌ Lỗi decode ảnh: {e}")
        return None
    
    # ƯU TIÊN 1: PaddleOCR (VIP)
    if PADDLEOCR_AVAILABLE:
        print("🔍 [ƯU TIÊN 1] Thử nhận dạng bằng PaddleOCR (VIP)...")
        result = detect_license_plate_with_paddleocr(img)
        if result:
            print(f"✅ PaddleOCR tìm thấy biển số: {result}")
            return result
    
    # ƯU TIÊN 2: EasyOCR
    if EASYOCR_AVAILABLE:
        print("🔍 [ƯU TIÊN 2] Thử nhận dạng bằng EasyOCR...")
        result = detect_license_plate_with_easyocr(img)
        if result:
            print(f"✅ EasyOCR tìm thấy biển số: {result}")
            return result
    
    # ƯU TIÊN 3: DTK LPR SDK
    if DTK_LPR_ENABLED and lpr_engine is not None:
        print("🔍 [ƯU TIÊN 3] Thử nhận dạng bằng DTK LPR SDK...")
        try:
            if image_path and os.path.exists(image_path):
                plates = lpr_engine.ReadFromFile(image_path)
            else:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                    tmp_file.write(image_data)
                    tmp_path = tmp_file.name
                try:
                    plates = lpr_engine.ReadFromFile(tmp_path)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
            
            if plates and len(plates) > 0:
                best_plate = max(plates, key=lambda p: p.Confidence)
                plate_text = best_plate.Text
                print(f"✅ DTK LPR SDK tìm thấy biển số: {plate_text}")
                for plate in plates:
                    plate.Dispose()
                return plate_text
        except Exception as e:
            print(f"⚠️  Lỗi DTK LPR SDK: {e}")
    
    print("⚠️  Không nhận dạng được biển số bằng bất kỳ phương pháp nào")
    return None

def detect_license_plate(image_data, image_path=None):
    """
    Wrapper function - tương thích với code cũ
    """
    print("🔍 Đang nhận dạng biển số bằng DTK LPR SDK...")
    result = detect_license_plate_from_image(image_data, image_path)
    if result:
        return result
    else:
        print("⚠️  Không nhận dạng được biển số")
        return None

def upload_data_file(license_plate, image_data, vehicle_weight=None, direction="IN"):
    try:
        # Generate random weight từ 3-5kg nếu không có weight
        if vehicle_weight is None:
            vehicle_weight = get_random_weight()
        
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
        # Generate random weight từ 3-5kg nếu không có weight
        if vehicle_weight is None:
            vehicle_weight = get_random_weight()
        
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
        # Generate random weight từ 3-5kg nếu không có weight
        if vehicle_weight is None:
            vehicle_weight = get_random_weight()
        
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
    # Generate random weight từ 3-5kg nếu không có weight
    if vehicle_weight is None:
        vehicle_weight = get_random_weight()
    
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

# ========== SERIAL & WEIGHT READING ==========

def parse_weight(line):
    """Parse trọng lượng từ dòng serial"""
    if "Weight stable:" in line:
        try:
            weight_str = line.split("Weight stable:")[1].strip().split()[0]
            return float(weight_str)
        except:
            return None
    return None

def serial_reader_thread(ser, cap):
    """
    Thread đọc dữ liệu từ ESP32 qua Serial
    """
    global scan_trigger, current_weight, scan_start_time, is_object_on_scale
    
    print("📡 Serial reader thread đang chạy...")
    
    while True:
        if ser and ser.in_waiting:
            try:
                line = ser.readline().decode(errors='ignore').strip()
                if not line:
                    continue
                
                # Parse trọng lượng
                w = parse_weight(line)
                if w is not None and w >= MIN_WEIGHT_KG:
                    if not is_object_on_scale:
                        print(f"\n⚖️  Phát hiện cân: {w}kg -> Bắt đầu quét biển số...")
                        current_weight = w
                        scan_start_time = time.time()
                        scan_trigger = True
                        is_object_on_scale = True
                
                # Kiểm tra vật đã được lấy ra
                if "Object removed" in line:
                    if is_object_on_scale:
                        print("🔄 Đã lấy vật ra. Reset.")
                        is_object_on_scale = False
                        scan_trigger = False
                        
            except Exception as e:
                print(f"⚠️  Lỗi đọc serial: {e}")
        
        time.sleep(0.1)  # Tránh CPU quá tải

def lpr_worker_thread(cap):
    """
    Thread xử lý nhận dạng biển số bằng DTK LPR SDK
    """
    global scan_trigger, current_weight, scan_start_time, latest_frame
    
    print("🔹 LPR Worker Thread đang chạy ngầm...")
    
    while True:
        if not scan_trigger:
            time.sleep(0.2)
            continue
        
        # Kiểm tra timeout
        if time.time() - scan_start_time > SCAN_TIMEOUT:
            print("⚠️  Hết giờ (Timeout) - Không đọc được biển số.")
            with frame_lock:
                if latest_frame is not None:
                    frame_copy = latest_frame.copy()
                    _, buffer = cv2.imencode('.jpg', frame_copy)
                    image_data = buffer.tobytes()
                    
                    # Upload với biển số "UNKNOWN"
                    upload_data_file("UNKNOWN", image_data, current_weight, "IN")
            
            scan_trigger = False
            continue
        
        # Throttling: Nghỉ 0.5s để đỡ lag
        time.sleep(0.5)
        
        # Chụp ảnh mới
        image_data, frame = capture_image_with_camera(camera_index=0, cap=cap)
        
        if image_data is None or frame is None:
            continue
        
        try:
            # Cập nhật latest_frame
            with frame_lock:
                latest_frame = frame.copy()
            
            # Nếu dùng DTK LPR với video stream
            if DTK_LPR_ENABLED and lpr_engine is not None:
                # Chuyển đổi frame thành format mà DTK LPR cần
                # VideoFrame hoặc numpy array tùy API
                # lpr_engine.PutFrame(frame, 0)
                pass
            else:
                # Dùng detect từ ảnh tĩnh
                license_plate = detect_license_plate_from_image(image_data)
                
                if license_plate and license_plate != "51A-TEST01":
                    print(f"🎯 TÌM THẤY BIỂN SỐ: {license_plate}")
                    upload_data_file(license_plate, image_data, current_weight, "IN")
                    scan_trigger = False  # Dừng quét
                else:
                    print("🔍 Đang quét... (chưa tìm thấy biển số)")
        
        except Exception as e:
            print(f"❌ Lỗi xử lý LPR: {e}")
            continue

def main(): 
    global latest_frame, scan_trigger, current_weight, scan_start_time, is_object_on_scale, last_trigger_time
    
    print("=" * 60)
    print("🍓 RASPBERRY PI - HỆ THỐNG CÂN XE & NHẬN DẠNG BIỂN SỐ")
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
    
    # Khởi tạo DTK LPR SDK
    if DTK_LPR_ENABLED:
        print("🔧 Khởi tạo DTK LPR SDK...")
        init_dtk_lpr()
        print()
    
    # Khởi tạo Camera
    print("📷 Khởi tạo camera...")
    cap = None
    for camera_idx in range(3):
        cap = cv2.VideoCapture(camera_idx)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            print(f"✅ Camera index {camera_idx} đã sẵn sàng")
            break
        else:
            if cap:
                cap.release()
            cap = None
    
    if cap is None:
        print("❌ Không thể mở camera!")
        print("   Vui lòng kiểm tra USB camera đã được cắm")
        return
    
    # Khởi tạo Serial (ESP32)
    print("📡 Khởi tạo kết nối Serial với ESP32...")
    ser = None
    try:
        # Thử các cổng serial phổ biến
        possible_ports = [SERIAL_PORT]
        if sys.platform.startswith('win'):
            # Windows: COM3, COM4, COM5...
            possible_ports = [f"COM{i}" for i in range(3, 10)]
        elif sys.platform.startswith('linux'):
            # Linux: /dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyACM0...
            possible_ports = [f"/dev/ttyUSB{i}" for i in range(3)] + [f"/dev/ttyACM{i}" for i in range(3)]
        
        for port in possible_ports:
            try:
                ser = serial.Serial(port, BAUD_RATE, timeout=0.02)
                print(f"✅ Kết nối Serial thành công: {port}")
                break
            except:
                continue
        
        if ser is None:
            print("⚠️  Không thể kết nối Serial với ESP32")
            print("   Hệ thống sẽ chạy ở chế độ TỰ ĐỘNG (Auto trigger mỗi 5 giây)")
            print("   💡 Mỗi 5 giây sẽ tự động trigger quét biển số")
    
    except Exception as e:
        print(f"⚠️  Lỗi khởi tạo Serial: {e}")
        print("   Hệ thống sẽ chạy ở chế độ TỰ ĐỘNG (Auto trigger mỗi 5 giây)")
    
    print()
    print("🚀 HỆ THỐNG SẴN SÀNG!")
    print("ℹ️  Mỗi 5 giây sẽ tự động trigger quét biển số (random cân 3-5kg)")
    print("ℹ️  Đặt biển số vào GIỮA màn hình để nhận diện tốt nhất.")
    print("ℹ️  Nhấn 'q' để thoát.")
    print()
    
    # Khởi động các thread
    if ser:
        t_serial = threading.Thread(target=serial_reader_thread, args=(ser, cap), daemon=True)
        t_serial.start()
    
    t_lpr = threading.Thread(target=lpr_worker_thread, args=(cap,), daemon=True)
    t_lpr.start()
    
    try:
        last_trigger_time = time.time()
        
        while True:
            # Main loop: Hiển thị camera
            ret, frame = cap.read()
            if ret:
                with frame_lock:
                    latest_frame = frame.copy()
                
                display = frame.copy()
                
                # Vẽ khung chữ nhật mô phỏng vùng nhận dạng
                h, w = display.shape[:2]
                cv2.rectangle(display, (int(w*0.15), int(h*0.2)), 
                             (int(w*0.85), int(h*0.8)), (0, 255, 255), 2)
                
                # Hiển thị trạng thái
                if scan_trigger:
                    elapsed = time.time() - scan_start_time
                    cv2.putText(display, f"SCANNING... ({elapsed:.1f}s)", (50, 50), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(display, f"Weight: {current_weight:.3f} kg", (50, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    time_until_next = 5 - (time.time() - last_trigger_time)
                    if time_until_next < 0:
                        time_until_next = 0
                    cv2.putText(display, f"READY - Next trigger in {time_until_next:.1f}s...", (50, 50), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow("Smart Scale - License Plate Recognition", display)
            
            # AUTO TRIGGER LOGIC: Mỗi 5 giây tự động trigger nếu không đang scan
            current_time = time.time()
            if not scan_trigger and (current_time - last_trigger_time) >= 5.0:
                # Auto-trigger mỗi 5 giây
                random_weight = get_random_weight()
                print(f"\n⏰ AUTO TRIGGER - Random cân: {random_weight}kg")
                print("📷 Bắt đầu quét biển số...")
                current_weight = random_weight
                scan_start_time = time.time()
                scan_trigger = True
                last_trigger_time = current_time
            
            # Xử lý phím bấm
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\n⚠️  Người dùng dừng chương trình")
    finally:
        # Cleanup
        cap.release()
        if ser:
            ser.close()
        cv2.destroyAllWindows()
        print("\n✅ Đã dừng hệ thống")

if __name__ == "__main__":
    main()

