"""
Script test nhận dạng biển số từ ảnh có sẵn
Đọc ảnh từ thư mục test/ và test các chức năng từ raspberry_pi_upload.py
Lưu ảnh kết quả (có vẽ box biển số) vào folder test/
"""

import sys
import os
import cv2
import numpy as np
import re
from datetime import datetime

# Thêm thư mục cha vào path để import raspberry_pi_upload
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raspberry_pi_upload import (
    detect_license_plate_from_image,
    detect_license_plate,
    upload_data_file,
    upload_image_to_imgbb
)

# Thử import DTK LPR SDK (nếu có) - ƯU TIÊN
try:
    from dtklpr import LPREngine, LPRParams
    DTK_LPR_AVAILABLE = True
except ImportError:
    try:
        from DTKLPR import LPREngine, LPRParams
        DTK_LPR_AVAILABLE = True
    except ImportError:
        DTK_LPR_AVAILABLE = False
        print("ℹ️  DTK LPR SDK chưa cài đặt. Sẽ dùng OCR thay thế.")

# Thử import EasyOCR (nếu có)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Thử import PaddleOCR (nếu có)
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

def load_and_convert_image(image_path):
    """
    Đọc ảnh từ file (hỗ trợ nhiều format: webp, jpg, png, ...)
    Trả về cả numpy array (img) và JPEG bytes (image_data)
    """
    try:
        print(f"📂 Đang đọc ảnh: {image_path}")
        
        # Đọc ảnh bằng OpenCV (hỗ trợ nhiều format)
        img = cv2.imread(image_path)
        
        if img is None:
            print(f"❌ Không thể đọc ảnh từ: {image_path}")
            print("   Kiểm tra:")
            print("   - File có tồn tại không?")
            print("   - Format ảnh có được hỗ trợ không?")
            return None, None
        
        print(f"✅ Đã đọc ảnh thành công!")
        print(f"   Kích thước: {img.shape[1]}x{img.shape[0]} pixels")
        
        # Chuyển đổi sang JPEG bytes
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        _, buffer = cv2.imencode('.jpg', img, encode_params)
        
        if buffer is None:
            print("❌ Không thể encode ảnh sang JPEG")
            return None, None
        
        image_data = buffer.tobytes()
        print(f"   Kích thước file JPEG: {len(image_data)} bytes")
        
        return img, image_data
        
    except Exception as e:
        print(f"❌ Lỗi đọc ảnh: {e}")
        return None, None

def is_vietnam_license_plate(text):
    """
    Kiểm tra xem text có phải biển số Việt Nam không
    Format: XX-XXXXX hoặc XXX-XXXXX (có thể có dấu chấm, khoảng trắng)
    Ví dụ: 60C-55555, 30A-12345, 60C 555.55, 60C55555
    """
    text_upper = text.upper().strip()
    
    # Loại bỏ khoảng trắng, dấu chấm, dấu gạch ngang để kiểm tra
    text_clean = re.sub(r'[\s\.\-]', '', text_upper)
    
    # Biển số VN thường có format: số + chữ + số
    # Tổng độ dài thường 7-10 ký tự
    if len(text_clean) < 6 or len(text_clean) > 10:
        return False
    
    # Phải có cả chữ và số
    has_letter = any(c.isalpha() for c in text_clean)
    has_digit = any(c.isdigit() for c in text_clean)
    
    if not (has_letter and has_digit):
        return False
    
    # Pattern 1: Số + Chữ + Số (ví dụ: 60C55555, 30A12345, T61679)
    # Format: (có thể có 1 chữ đầu) + 2-3 số + 0-2 chữ + 4-6 số
    pattern1 = re.match(r'^[A-Z]?\d{2,3}[A-Z]{0,2}\d{4,6}$', text_clean)
    
    # Pattern 2: Chữ + Số (ví dụ: ABC12345) - ít phổ biến hơn
    pattern2 = re.match(r'^[A-Z]{2,3}\d{4,7}$', text_clean)
    
    # Pattern 3: Kiểm tra format có khoảng trắng/dấu chấm (ví dụ: "60C 555.55", "T61 679.60")
    # Tách thành phần: số + chữ và số
    parts = re.split(r'[\s\.\-]+', text_upper)
    if len(parts) == 2:
        part1 = re.sub(r'[\s\.\-]', '', parts[0].strip())
        part2 = re.sub(r'[\s\.\-]', '', parts[1].strip())
        # Phần 1: có thể là chữ + số (ví dụ: "T61", "60C", "30A")
        # Phần 2: số (ví dụ: "55555", "67960", "1679")
        part1_match = (re.match(r'^[A-Z]?\d{2,3}[A-Z]{0,2}$', part1) or 
                       re.match(r'^\d{2,3}[A-Z]{1,2}$', part1))
        part2_match = re.match(r'^\d{3,6}$', part2)
        if part1_match and part2_match:
            return True
    
    # Pattern 4: Format đặc biệt như "T61 679.60" - có thể bị tách thành "T61" và "1679"
    # Nếu text_clean có dạng T61xxxxx (T + số + số) cũng có thể là biển số
    if re.match(r'^[A-Z]\d{2,3}\d{4,6}$', text_clean):
        return True
    
    return bool(pattern1 or pattern2)

def combine_nearby_texts(results, max_distance=100):
    """
    Ghép các text gần nhau lại thành biển số hoàn chỉnh
    Ví dụ: "60C" + "555.55" = "60C 555.55"
    """
    if not results:
        return []
    
    h, w = 0, 0
    if results:
        # Lấy kích thước ảnh từ bbox đầu tiên
        first_bbox = results[0][0]
        h = max(pt[1] for pt in first_bbox) * 2
        w = max(pt[0] for pt in first_bbox) * 2
    
    combined = []
    used = set()
    
    for i, (bbox1, text1, conf1) in enumerate(results):
        if i in used:
            continue
        
        # Tính center của bbox1
        x1_center = sum(pt[0] for pt in bbox1) / len(bbox1)
        y1_center = sum(pt[1] for pt in bbox1) / len(bbox1)
        
        # Tìm các text gần nhau theo chiều ngang (cùng hàng)
        nearby_texts = [(text1, conf1, bbox1)]
        used.add(i)
        
        for j, (bbox2, text2, conf2) in enumerate(results):
            if j in used or i == j:
                continue
            
            x2_center = sum(pt[0] for pt in bbox2) / len(bbox2)
            y2_center = sum(pt[1] for pt in bbox2) / len(bbox2)
            
            # Khoảng cách ngang và dọc
            dx = abs(x2_center - x1_center)
            dy = abs(y2_center - y1_center)
            
            # Nếu cùng hàng (dy nhỏ) và gần nhau theo chiều ngang
            if dy < 50 and dx < max_distance:
                nearby_texts.append((text2, conf2, bbox2))
                used.add(j)
        
        # Sắp xếp theo x để ghép đúng thứ tự
        nearby_texts.sort(key=lambda x: sum(pt[0] for pt in x[2]) / len(x[2]))
        
        # Ghép text lại
        combined_text = ' '.join(t[0] for t in nearby_texts)
        avg_confidence = sum(t[1] for t in nearby_texts) / len(nearby_texts)
        
        # Tạo bbox tổng hợp (bounding box của tất cả text)
        all_points = []
        for _, _, bbox in nearby_texts:
            all_points.extend(bbox)
        
        combined_bbox = [
            [min(pt[0] for pt in all_points), min(pt[1] for pt in all_points)],
            [max(pt[0] for pt in all_points), min(pt[1] for pt in all_points)],
            [max(pt[0] for pt in all_points), max(pt[1] for pt in all_points)],
            [min(pt[0] for pt in all_points), max(pt[1] for pt in all_points)]
        ]
        
        combined.append((combined_bbox, combined_text, avg_confidence))
    
    return combined

def detect_license_plate_with_easyocr(img):
    """
    Nhận dạng biển số bằng EasyOCR
    Tập trung vào biển số Việt Nam, loại bỏ text khác trên xe
    """
    if not EASYOCR_AVAILABLE:
        return None, None
    
    try:
        print("🔍 Đang khởi tạo EasyOCR (lần đầu có thể mất vài phút)...")
        reader = easyocr.Reader(['en', 'vi'], gpu=False)
        
        print("🔍 Đang nhận dạng text từ ảnh...")
        results = reader.readtext(img)
        
        if not results:
            print("⚠️  Không tìm thấy text nào trong ảnh")
            return None, None
        
        # Ghép các text gần nhau lại (ví dụ: "60C" + "555.55" = "60C 555.55")
        print("🔗 Đang ghép các text gần nhau...")
        combined_results = combine_nearby_texts(results)
        
        # Lọc và tìm biển số
        license_plate_candidates = []
        h, w = img.shape[:2]
        
        # Kiểm tra cả text gốc và text đã ghép
        all_results = list(results) + combined_results
        
        for item in all_results:
            if len(item) == 3:
                bbox, text, confidence = item
            else:
                continue
                
            text_clean = text.strip().upper()
            
            # Bỏ qua text quá ngắn hoặc quá dài
            if len(text_clean) < 3 or len(text_clean) > 20:
                continue
            
            # Bỏ qua text chỉ có chữ (như "THACO", "FORLAND")
            if text_clean.isalpha() and len(text_clean) > 5:
                continue
            
            # Kiểm tra format biển số Việt Nam
            if is_vietnam_license_plate(text_clean):
                # Tính vị trí Y trung bình của bbox
                y_center = sum(pt[1] for pt in bbox) / len(bbox)
                position_score = 1.0 if y_center > h * 0.5 else 0.5
                
                license_plate_candidates.append({
                    'text': text_clean,
                    'bbox': bbox,
                    'confidence': confidence,
                    'position_score': position_score,
                    'total_score': confidence * position_score
                })
                print(f"  📋 Tìm thấy candidate: {text_clean} (confidence: {confidence:.2%}, vị trí: {y_center:.0f}px)")
        
        if license_plate_candidates:
            # Chọn candidate có điểm cao nhất
            best = max(license_plate_candidates, key=lambda x: x['total_score'])
            print(f"✅ Tìm thấy biển số: {best['text']} (độ tin cậy: {best['confidence']:.2%})")
            return best['text'], best['bbox']
        else:
            print("⚠️  Không tìm thấy text nào có format biển số Việt Nam")
            print("   Các text tìm thấy:")
            for (bbox, text, conf) in results[:5]:
                print(f"     - '{text}' (confidence: {conf:.2%})")
            # Thử ghép thủ công nếu thấy pattern biển số
            print("\n🔍 Thử ghép các text có vẻ là biển số...")
            # Tìm text có vẻ là phần đầu biển số (số + chữ, như "T61", "60C")
            plate_prefixes = []
            plate_suffixes = []
            
            for (bbox, text, conf) in results:
                text_clean = text.strip().upper()
                # Phần đầu: số + chữ (ví dụ: T61, 60C, 30A)
                if re.match(r'^[A-Z]?\d{2,3}[A-Z]{0,2}$', text_clean) or re.match(r'^\d{2,3}[A-Z]{1,2}$', text_clean):
                    y_center = sum(pt[1] for pt in bbox) / len(bbox)
                    plate_prefixes.append((bbox, text_clean, conf, y_center))
                # Phần sau: số (ví dụ: 1679, 679.60, 555.55)
                elif re.match(r'^\d{3,6}(\.\d{1,2})?$', text_clean):
                    y_center = sum(pt[1] for pt in bbox) / len(bbox)
                    plate_suffixes.append((bbox, text_clean, conf, y_center))
            
            # Thử ghép prefix và suffix gần nhau
            for (bbox1, text1, conf1, y1) in plate_prefixes:
                for (bbox2, text2, conf2, y2) in plate_suffixes:
                    # Kiểm tra xem có cùng hàng không (y gần nhau)
                    if abs(y1 - y2) < 50:
                        # Kiểm tra xem có gần nhau theo chiều ngang không
                        x1_center = sum(pt[0] for pt in bbox1) / len(bbox1)
                        x2_center = sum(pt[0] for pt in bbox2) / len(bbox2)
                        if x2_center > x1_center and (x2_center - x1_center) < 200:
                            combined = f"{text1} {text2}".upper().strip()
                            if is_vietnam_license_plate(combined):
                                print(f"  ✅ Ghép thành công: {combined}")
                                # Tạo bbox tổng hợp
                                all_pts = list(bbox1) + list(bbox2)
                                combined_bbox = [
                                    [min(pt[0] for pt in all_pts), min(pt[1] for pt in all_pts)],
                                    [max(pt[0] for pt in all_pts), min(pt[1] for pt in all_pts)],
                                    [max(pt[0] for pt in all_pts), max(pt[1] for pt in all_pts)],
                                    [min(pt[0] for pt in all_pts), max(pt[1] for pt in all_pts)]
                                ]
                                return combined, combined_bbox
            
            # Nếu không ghép được, thử tất cả các cặp
            print("  🔄 Thử ghép tất cả các cặp text...")
            for (bbox1, text1, conf1) in results:
                for (bbox2, text2, conf2) in results:
                    if text1 == text2:
                        continue
                    combined = f"{text1} {text2}".upper().strip()
                    if is_vietnam_license_plate(combined):
                        print(f"  ✅ Ghép thành công: {combined}")
                        all_pts = list(bbox1) + list(bbox2)
                        combined_bbox = [
                            [min(pt[0] for pt in all_pts), min(pt[1] for pt in all_pts)],
                            [max(pt[0] for pt in all_pts), min(pt[1] for pt in all_pts)],
                            [max(pt[0] for pt in all_pts), max(pt[1] for pt in all_pts)],
                            [min(pt[0] for pt in all_pts), max(pt[1] for pt in all_pts)]
                        ]
                        return combined, combined_bbox
            return None, None
        
    except Exception as e:
        print(f"❌ Lỗi EasyOCR: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def detect_license_plate_with_paddleocr(img):
    """
    Nhận dạng biển số bằng PaddleOCR (VIP - chính xác và nhanh)
    Tập trung vào biển số Việt Nam, loại bỏ text khác trên xe
    """
    if not PADDLEOCR_AVAILABLE:
        return None, None
    
    try:
        print("🔍 Đang khởi tạo PaddleOCR (VIP)...")
        ocr = PaddleOCR(use_textline_orientation=True, lang='vi')
        
        print("🔍 Đang nhận dạng text từ ảnh...")
        # Dùng predict() vì ocr() đã deprecated
        try:
            predict_result = ocr.predict(img)
            print(f"  📊 predict() trả về type: {type(predict_result)}")
            
            # Parse từ OCRResult object hoặc dict
            easyocr_format = []
            
            # Nếu là list, lấy item đầu tiên (thường là OCRResult object)
            if isinstance(predict_result, list) and len(predict_result) > 0:
                result_obj = predict_result[0]
            else:
                result_obj = predict_result
            
            # Truy cập thuộc tính từ OCRResult object
            if hasattr(result_obj, 'rec_texts'):
                rec_texts = result_obj.rec_texts
                rec_scores = result_obj.rec_scores
                rec_polys = result_obj.rec_polys
            elif isinstance(result_obj, dict):
                rec_texts = result_obj.get('rec_texts', [])
                rec_scores = result_obj.get('rec_scores', [])
                rec_polys = result_obj.get('rec_polys', [])
            else:
                print(f"  ⚠️  Không thể truy cập rec_texts từ {type(result_obj)}")
                return None, None
            
            print(f"  📊 Tìm thấy {len(rec_texts)} text(s)")
            print(f"  📝 Các text: {rec_texts[:10]}")
            
            # Tạo format giống EasyOCR: [(bbox, text, confidence)]
            for poly, text, score in zip(rec_polys, rec_texts, rec_scores):
                easyocr_format.append((poly, text, float(score)))
                print(f"    ✅ '{text}' (score: {score:.2%})")
                
        except Exception as e:
            print(f"❌ Lỗi khi gọi PaddleOCR: {e}")
            import traceback
            traceback.print_exc()
            return None, None
        
        if not easyocr_format:
            print("⚠️  Không parse được text nào từ PaddleOCR")
            return None, None
        
        print(f"  ✅ Đã parse được {len(easyocr_format)} text(s) từ PaddleOCR")
        
        # Lọc và tìm biển số
        license_plate_candidates = []
        h, w = img.shape[:2]
        
        for (bbox, text, confidence) in easyocr_format:
            text_clean = text.strip().upper()
            
            # Bỏ qua text quá ngắn hoặc quá dài
            if len(text_clean) < 3 or len(text_clean) > 20:
                continue
            
            # Bỏ qua text chỉ có chữ (như "THACO", "FORLAND")
            if text_clean.isalpha() and len(text_clean) > 5:
                continue
            
            # Kiểm tra format biển số Việt Nam
            if is_vietnam_license_plate(text_clean):
                # Tính vị trí Y trung bình của bbox
                y_center = sum(pt[1] for pt in bbox) / len(bbox)
                position_score = 1.0 if y_center > h * 0.5 else 0.5
                
                license_plate_candidates.append({
                    'text': text_clean,
                    'bbox': bbox,
                    'confidence': confidence,
                    'position_score': position_score,
                    'total_score': confidence * position_score
                })
                print(f"  📋 Tìm thấy candidate: {text_clean} (confidence: {confidence:.2%}, vị trí: {y_center:.0f}px)")
        
        if license_plate_candidates:
            # Chọn candidate có điểm cao nhất
            best = max(license_plate_candidates, key=lambda x: x['total_score'])
            print(f"✅ Tìm thấy biển số: {best['text']} (độ tin cậy: {best['confidence']:.2%})")
            return best['text'], best['bbox']
        else:
            print("⚠️  Không tìm thấy text nào có format biển số Việt Nam")
            print("   Các text tìm thấy:")
            for (bbox, text, conf) in easyocr_format[:5]:
                print(f"     - '{text}' (confidence: {conf:.2%})")
            
            # Thử ghép thủ công nếu thấy pattern biển số (giống EasyOCR)
            print("\n🔍 Thử ghép các text có vẻ là biển số...")
            plate_prefixes = []
            plate_suffixes = []
            
            for (bbox, text, conf) in easyocr_format:
                text_clean = text.strip().upper()
                # Phần đầu: số + chữ (ví dụ: T61, 60C, 30A)
                if re.match(r'^[A-Z]?\d{2,3}[A-Z]{0,2}$', text_clean) or re.match(r'^\d{2,3}[A-Z]{1,2}$', text_clean):
                    y_center = sum(pt[1] for pt in bbox) / len(bbox)
                    plate_prefixes.append((bbox, text_clean, conf, y_center))
                # Phần sau: số (ví dụ: 1679, 679.60, 555.55)
                elif re.match(r'^\d{3,6}(\.\d{1,2})?$', text_clean):
                    y_center = sum(pt[1] for pt in bbox) / len(bbox)
                    plate_suffixes.append((bbox, text_clean, conf, y_center))
            
            # Thử ghép prefix và suffix gần nhau
            for (bbox1, text1, conf1, y1) in plate_prefixes:
                for (bbox2, text2, conf2, y2) in plate_suffixes:
                    # Kiểm tra xem có cùng hàng không (y gần nhau)
                    if abs(y1 - y2) < 50:
                        # Kiểm tra xem có gần nhau theo chiều ngang không
                        x1_center = sum(pt[0] for pt in bbox1) / len(bbox1)
                        x2_center = sum(pt[0] for pt in bbox2) / len(bbox2)
                        if x2_center > x1_center and (x2_center - x1_center) < 200:
                            combined = f"{text1} {text2}".upper().strip()
                            if is_vietnam_license_plate(combined):
                                print(f"  ✅ Ghép thành công: {combined}")
                                # Tạo bbox tổng hợp
                                all_pts = list(bbox1) + list(bbox2)
                                combined_bbox = [
                                    [min(pt[0] for pt in all_pts), min(pt[1] for pt in all_pts)],
                                    [max(pt[0] for pt in all_pts), min(pt[1] for pt in all_pts)],
                                    [max(pt[0] for pt in all_pts), max(pt[1] for pt in all_pts)],
                                    [min(pt[0] for pt in all_pts), max(pt[1] for pt in all_pts)]
                                ]
                                return combined, combined_bbox
            
            # Nếu không ghép được, thử tất cả các cặp
            print("  🔄 Thử ghép tất cả các cặp text...")
            for (bbox1, text1, conf1) in easyocr_format:
                for (bbox2, text2, conf2) in easyocr_format:
                    if text1 == text2:
                        continue
                    combined = f"{text1} {text2}".upper().strip()
                    if is_vietnam_license_plate(combined):
                        print(f"  ✅ Ghép thành công: {combined}")
                        all_pts = list(bbox1) + list(bbox2)
                        combined_bbox = [
                            [min(pt[0] for pt in all_pts), min(pt[1] for pt in all_pts)],
                            [max(pt[0] for pt in all_pts), min(pt[1] for pt in all_pts)],
                            [max(pt[0] for pt in all_pts), max(pt[1] for pt in all_pts)],
                            [min(pt[0] for pt in all_pts), max(pt[1] for pt in all_pts)]
                        ]
                        return combined, combined_bbox
            
            return None, None
        
    except Exception as e:
        print(f"❌ Lỗi PaddleOCR: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def draw_license_plate_result(img, license_plate, bbox=None):
    """
    Vẽ box và text biển số lên ảnh
    """
    result_img = img.copy()
    
    if bbox is not None:
        # Vẽ box (bbox có thể là list of points hoặc rectangle)
        if isinstance(bbox, list) and len(bbox) > 0:
            # EasyOCR format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            if isinstance(bbox[0], (list, tuple, np.ndarray)):
                pts = np.array(bbox, dtype=np.int32)
                cv2.polylines(result_img, [pts], isClosed=True, color=(0, 255, 0), thickness=3)
                # Lấy tọa độ để vẽ text
                x_min = int(min(pt[0] for pt in bbox))
                y_min = int(min(pt[1] for pt in bbox))
            else:
                # Rectangle format
                x_min, y_min = int(bbox[0]), int(bbox[1])
                x_max, y_max = int(bbox[2]), int(bbox[3])
                cv2.rectangle(result_img, (x_min, y_min), (x_max, y_max), (0, 255, 0), 3)
        else:
            x_min, y_min = 50, 50
    else:
        x_min, y_min = 50, 50
    
    # Vẽ text biển số
    if license_plate:
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        thickness = 2
        
        # Tính kích thước text để vẽ background
        (text_width, text_height), baseline = cv2.getTextSize(
            license_plate, font, font_scale, thickness
        )
        
        # Vẽ background cho text
        cv2.rectangle(
            result_img,
            (x_min, y_min - text_height - 10),
            (x_min + text_width + 10, y_min + 10),
            (0, 255, 0),
            -1
        )
        
        # Vẽ text
        cv2.putText(
            result_img,
            license_plate,
            (x_min + 5, y_min - 5),
            font,
            font_scale,
            (0, 0, 0),
            thickness
        )
    
    return result_img

def save_result_image(img, license_plate, output_dir):
    """
    Lưu ảnh kết quả vào folder test
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{license_plate.replace(' ', '_')}_{timestamp}.jpg"
        output_path = os.path.join(output_dir, filename)
        
        cv2.imwrite(output_path, img)
        print(f"💾 Đã lưu ảnh kết quả: {filename}")
        return output_path
    except Exception as e:
        print(f"❌ Lỗi lưu ảnh: {e}")
        return None

def detect_license_plate_with_dtk_lpr(image_path):
    """
    Nhận dạng biển số bằng DTK LPR SDK (giống C#: engine.ReadFromFile)
    """
    if not DTK_LPR_AVAILABLE:
        return None, None
    
    try:
        print("🔍 Đang khởi tạo DTK LPR Engine...")
        # Tạo LPR Parameters (giống C#)
        params = LPRParams()
        params.Countries = "VN,US,DE,NL,DK,PL"  # Có thể thêm VN cho biển số Việt Nam
        params.MinPlateWidth = 80
        params.MaxPlateWidth = 300
        
        # Khởi tạo engine (False = không dùng callback cho ảnh tĩnh)
        engine = LPREngine(params, False, None)
        
        print(f"📸 Đang đọc biển số từ file: {image_path}")
        # Tương tự C#: List<LicensePlate> plates = engine.ReadFromFile("C:/Images/test.jpg")
        plates = engine.ReadFromFile(image_path)
        
        if plates and len(plates) > 0:
            # Lấy biển số có confidence cao nhất
            best_plate = max(plates, key=lambda p: p.Confidence)
            plate_text = best_plate.Text
            country = best_plate.CountryCode
            confidence = best_plate.Confidence
            
            print(f"✅ Tìm thấy biển số: {plate_text}")
            print(f"   Quốc gia: {country}, Độ tin cậy: {confidence:.2f}%")
            
            # Lấy bbox từ plate (nếu có)
            bbox = None
            if hasattr(best_plate, 'BoundingBox'):
                bbox = best_plate.BoundingBox
            
            # Dispose plates (giống C#: plate.Dispose())
            for plate in plates:
                plate.Dispose()
            
            return plate_text, bbox
        else:
            print("⚠️  Không tìm thấy biển số trong ảnh")
            return None, None
        
    except Exception as e:
        print(f"❌ Lỗi DTK LPR SDK: {e}")
        return None, None

def test_license_plate_detection(img, image_data, image_path):
    """
    Test nhận dạng biển số từ ảnh bằng nhiều phương pháp
    Ưu tiên: DTK LPR SDK > PaddleOCR > EasyOCR > raspberry_pi_upload
    """
    print("\n" + "=" * 60)
    print("🔍 BƯỚC 1: NHẬN DẠNG BIỂN SỐ")
    print("=" * 60)
    
    license_plate = None
    bbox = None
    
    # ƯU TIÊN 1: Thử DTK LPR SDK trước (chuyên dụng nhất)
    if DTK_LPR_AVAILABLE:
        print("\n📸 [ƯU TIÊN 1] Thử nhận dạng bằng DTK LPR SDK...")
        license_plate, bbox = detect_license_plate_with_dtk_lpr(image_path)
    
    # ƯU TIÊN 2: Thử PaddleOCR (VIP - chính xác và nhanh)
    if not license_plate and PADDLEOCR_AVAILABLE:
        print("\n📸 [ƯU TIÊN 2] Thử nhận dạng bằng PaddleOCR (VIP)...")
        license_plate, bbox = detect_license_plate_with_paddleocr(img)
    
    # ƯU TIÊN 3: Thử EasyOCR (fallback)
    if not license_plate and EASYOCR_AVAILABLE:
        print("\n📸 [ƯU TIÊN 3] Thử nhận dạng bằng EasyOCR...")
        license_plate, bbox = detect_license_plate_with_easyocr(img)
    
    # ƯU TIÊN 4: Thử hàm từ raspberry_pi_upload.py (chỉ nếu DTK LPR được enable)
    if not license_plate:
        print("\n📸 Thử nhận dạng bằng hàm từ raspberry_pi_upload.py...")
        license_plate = detect_license_plate_from_image(image_data, image_path)
        if license_plate:
            print(f"✅ BIỂN SỐ ĐÃ NHẬN DẠNG: {license_plate}")
        else:
            license_plate = None
    
    # Nếu vẫn không có kết quả, báo lỗi rõ ràng
    if not license_plate:
        print("\n" + "=" * 60)
        print("⚠️  KHÔNG NHẬN DẠNG ĐƯỢC BIỂN SỐ")
        print("=" * 60)
        print("Các phương pháp đã thử:")
        if not DTK_LPR_AVAILABLE:
            print("  ❌ DTK LPR SDK: Chưa cài đặt")
        if not EASYOCR_AVAILABLE:
            print("  ❌ EasyOCR: Chưa cài đặt (cài: pip install easyocr)")
        if not PADDLEOCR_AVAILABLE:
            print("  ❌ PaddleOCR: Chưa cài đặt (cài: pip install paddlepaddle paddleocr)")
        print("\n💡 Đề xuất: Cài đặt ít nhất một trong các thư viện trên để nhận dạng biển số")
        license_plate = "UNKNOWN"
    
    return license_plate, bbox

def test_upload_to_imgbb(image_data):
    """
    Test upload ảnh lên ImgBB
    """
    print("\n" + "=" * 60)
    print("📤 BƯỚC 2: UPLOAD ẢNH LÊN IMGBB")
    print("=" * 60)
    
    image_url = upload_image_to_imgbb(image_data)
    
    if image_url:
        print(f"✅ Upload thành công!")
        print(f"   URL: {image_url}")
        return image_url
    else:
        print("❌ Upload thất bại")
        return None

def test_upload_to_server(license_plate, image_data, image_url=None):
    """
    Test upload dữ liệu lên server
    """
    print("\n" + "=" * 60)
    print("📤 BƯỚC 3: UPLOAD DỮ LIỆU LÊN SERVER")
    print("=" * 60)
    
    # Test weight (giả lập)
    test_weight = 1.5  # 1.5 tấn
    
    print(f"📋 Thông tin upload:")
    print(f"   🚗 Biển số: {license_plate}")
    print(f"   ⚖️  Khối lượng: {test_weight} tấn")
    print(f"   📸 Ảnh: {'Có URL' if image_url else 'Gửi trực tiếp'}")
    
    success = upload_data_file(
        license_plate=license_plate,
        image_data=image_data,
        vehicle_weight=test_weight,
        direction="IN"
    )
    
    if success:
        print("\n✅ HOÀN TẤT - Upload thành công lên server!")
    else:
        print("\n❌ Upload thất bại")
    
    return success

def main():
    import sys
    
    print("=" * 60)
    print("🧪 TEST NHẬN DẠNG BIỂN SỐ TỪ ẢNH")
    print("=" * 60)
    print()
    
    # Hiển thị các phương pháp có sẵn
    print("📋 Phương pháp nhận dạng có sẵn:")
    if DTK_LPR_AVAILABLE:
        print("  ✅ DTK LPR SDK (Ưu tiên cao nhất)")
    else:
        print("  ❌ DTK LPR SDK: Chưa cài đặt")
    if EASYOCR_AVAILABLE:
        print("  ✅ EasyOCR")
    else:
        print("  ❌ EasyOCR: Chưa cài đặt")
    if PADDLEOCR_AVAILABLE:
        print("  ✅ PaddleOCR")
    else:
        print("  ❌ PaddleOCR: Chưa cài đặt")
    print()
    
    # Đường dẫn ảnh test - có thể truyền qua tham số hoặc dùng mặc định
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) > 1:
        # Nếu có tham số, dùng file đó
        image_path = sys.argv[1]
        if not os.path.isabs(image_path):
            image_path = os.path.join(script_dir, image_path)
    else:
        # Mặc định dùng bien-so-xe-tai.jpg
        image_path = os.path.join(script_dir, "bien-so.jpg")
        # Nếu không có, thử bien_so.webp
        if not os.path.exists(image_path):
            image_path = os.path.join(script_dir, "bien_so.webp")
    
    # Kiểm tra file tồn tại
    if not os.path.exists(image_path):
        print(f"❌ Không tìm thấy file: {image_path}")
        print("   Vui lòng đảm bảo file ảnh tồn tại trong thư mục test/")
        return
    
    # Bước 1: Đọc và chuyển đổi ảnh
    print("\n" + "=" * 60)
    print("📂 BƯỚC 0: ĐỌC ẢNH")
    print("=" * 60)
    img, image_data = load_and_convert_image(image_path)
    
    if img is None or image_data is None:
        print("\n❌ Không thể đọc ảnh. Dừng test.")
        return
    
    # Bước 2: Nhận dạng biển số
    license_plate, bbox = test_license_plate_detection(img, image_data, image_path)
    
    # Bước 3: Vẽ kết quả lên ảnh và lưu
    print("\n" + "=" * 60)
    print("🎨 BƯỚC 2: VẼ KẾT QUẢ LÊN ẢNH")
    print("=" * 60)
    result_img = draw_license_plate_result(img, license_plate, bbox)
    result_path = save_result_image(result_img, license_plate, script_dir)
    
    # Chuyển đổi ảnh kết quả thành bytes để upload
    _, buffer = cv2.imencode('.jpg', result_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    result_image_data = buffer.tobytes()
    
    # Bước 4: Upload ảnh lên ImgBB (optional, để test)
    image_url = test_upload_to_imgbb(result_image_data)
    
    # Bước 5: Upload lên server
    test_upload_to_server(license_plate, result_image_data, image_url)
    
    print("\n" + "=" * 60)
    print("✅ TEST HOÀN TẤT")
    print("=" * 60)

if __name__ == "__main__":
    main()

