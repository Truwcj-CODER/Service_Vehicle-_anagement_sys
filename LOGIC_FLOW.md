# 🔄 LOGIC HOẠT ĐỘNG CỦA HỆ THỐNG NHẬN DẠNG BIỂN SỐ

## 📋 TỔNG QUAN

Hệ thống tự động nhận dạng biển số xe từ camera, đo trọng lượng từ cân, và upload dữ liệu lên server.

---

## 🚀 LUỒNG HOẠT ĐỘNG CHÍNH

### 1. **KHỞI ĐỘNG HỆ THỐNG** (`main()`)

```
┌─────────────────────────────────────┐
│ 1. Kiểm tra kết nối server          │
│ 2. Khởi tạo DTK LPR SDK (nếu có)    │
│ 3. Khởi tạo Camera                   │
│ 4. Khởi tạo Serial (ESP32 - Cân)    │
│ 5. Khởi động các Thread              │
└─────────────────────────────────────┘
```

**Các Thread chạy song song:**
- `serial_reader_thread`: Đọc dữ liệu từ cân ESP32
- `lpr_worker_thread`: Xử lý nhận dạng biển số
- `main loop`: Hiển thị camera và xử lý phím bấm

---

### 2. **PHÁT HIỆN VẬT TRÊN CÂN** (`serial_reader_thread`)

```
ESP32 gửi: "Weight stable: 1.5kg"
    ↓
Kiểm tra: weight >= MIN_WEIGHT_KG (0.03kg)?
    ↓
CÓ → Kích hoạt scan_trigger = True
     Lưu current_weight
     Bắt đầu đếm thời gian (scan_start_time)
```

**Logic:**
- Đọc liên tục từ Serial port
- Parse trọng lượng từ dòng text
- Khi phát hiện vật ≥ 30g → bắt đầu quét biển số

---

### 3. **NHẬN DẠNG BIỂN SỐ** (`lpr_worker_thread`)

Khi `scan_trigger = True`, thread này sẽ:

```
┌─────────────────────────────────────────┐
│ Bước 1: Chụp ảnh từ camera             │
│   - capture_image_with_camera()        │
│   - Lưu vào latest_frame                │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Bước 2: Nhận dạng biển số              │
│   detect_license_plate_from_image()    │
└─────────────────────────────────────────┘
```

---

## 🔍 LOGIC NHẬN DẠNG BIỂN SỐ (Chi tiết)

### **Thứ tự ưu tiên:**

```
┌─────────────────────────────────────┐
│ ƯU TIÊN 1: PaddleOCR (VIP)         │
│   - Chính xác nhất                 │
│   - Nhanh nhất                      │
└─────────────────────────────────────┘
              ↓ (Nếu không tìm thấy)
┌─────────────────────────────────────┐
│ ƯU TIÊN 2: EasyOCR                 │
│   - Fallback                        │
│   - Dễ cài đặt                      │
└─────────────────────────────────────┘
              ↓ (Nếu không tìm thấy)
┌─────────────────────────────────────┐
│ ƯU TIÊN 3: DTK LPR SDK             │
│   - Chuyên dụng (cần license)       │
│   - Giống code C#                   │
└─────────────────────────────────────┘
```

---

### **Bước 1: OCR đọc tất cả text trong ảnh**

**PaddleOCR:**
```python
ocr = PaddleOCR(use_textline_orientation=True, lang='vi')
predict_result = ocr.predict(img)
# Trả về: rec_texts, rec_scores, rec_polys
```

**EasyOCR:**
```python
reader = easyocr.Reader(['en', 'vi'], gpu=False)
results = reader.readtext(img)
# Trả về: [(bbox, text, confidence), ...]
```

**Kết quả ví dụ:**
```
- "THACO" (confidence: 99%)
- "FORLAND" (confidence: 90%)
- "T61" (confidence: 63%)
- "1679" (confidence: 95%)
```

---

### **Bước 2: Lọc text - Loại bỏ text không phải biển số**

```python
for text in all_texts:
    # ❌ Bỏ qua text quá ngắn/dài
    if len(text) < 3 or len(text) > 20:
        continue
    
    # ❌ Bỏ qua text chỉ có chữ (như "THACO", "FORLAND")
    if text.isalpha() and len(text) > 5:
        continue
    
    # ✅ Kiểm tra format biển số VN
    if is_vietnam_license_plate(text):
        candidates.append(text)
```

**Kết quả sau lọc:**
```
- "T61" ✅ (có số + chữ)
- "1679" ✅ (có số)
- "THACO" ❌ (chỉ có chữ)
- "FORLAND" ❌ (chỉ có chữ)
```

---

### **Bước 3: Kiểm tra format biển số Việt Nam**

Hàm `is_vietnam_license_plate()` kiểm tra:

**Pattern 1:** `60C55555`, `30A12345`, `T61679`
- Format: `[A-Z]?\d{2,3}[A-Z]{0,2}\d{4,6}`

**Pattern 2:** `ABC12345` (ít phổ biến)
- Format: `[A-Z]{2,3}\d{4,7}`

**Pattern 3:** `60C 555.55`, `T61 679.60` (có khoảng trắng/dấu chấm)
- Tách thành 2 phần:
  - Phần 1: `60C`, `T61` (số + chữ)
  - Phần 2: `55555`, `67960` (số)

**Ví dụ:**
```python
"60C 555.55" → ✅ Biển số hợp lệ
"T61 1679" → ✅ Biển số hợp lệ
"THACO" → ❌ Không phải biển số
```

---

### **Bước 4: Ghép text bị tách rời**

**Vấn đề:** OCR thường tách biển số thành 2 phần:
- `"T61"` + `"1679"` thay vì `"T61 1679"`

**Giải pháp:**

```python
# Tìm prefix (phần đầu): "T61", "60C", "30A"
plate_prefixes = []
for text in texts:
    if re.match(r'^[A-Z]?\d{2,3}[A-Z]{0,2}$', text):
        plate_prefixes.append((text, y_position))

# Tìm suffix (phần sau): "1679", "555.55"
plate_suffixes = []
for text in texts:
    if re.match(r'^\d{3,6}(\.\d{1,2})?$', text):
        plate_suffixes.append((text, y_position))

# Ghép các text cùng hàng (y gần nhau)
for prefix, y1 in plate_prefixes:
    for suffix, y2 in plate_suffixes:
        if abs(y1 - y2) < 50:  # Cùng hàng
            combined = f"{prefix} {suffix}"
            if is_vietnam_license_plate(combined):
                return combined  # ✅ "T61 1679"
```

---

### **Bước 5: Chọn biển số tốt nhất**

Nếu có nhiều candidate:

```python
candidates = [
    {'text': 'T61 1679', 'confidence': 0.95, 'position': 0.8},
    {'text': '60C 555.55', 'confidence': 0.90, 'position': 0.6}
]

# Tính điểm: confidence × position_score
# Ưu tiên text ở nửa dưới ảnh (biển số thường ở đó)
best = max(candidates, key=lambda x: x['confidence'] * x['position_score'])
return best['text']  # "T61 1679"
```

---

## 📤 LOGIC UPLOAD LÊN SERVER

### **Bước 1: Upload ảnh lên ImgBB**

```python
image_url = upload_image_to_imgbb(image_data)
# Trả về: "https://i.ibb.co/xxxxx/image.jpg"
```

### **Bước 2: Gửi dữ liệu lên server**

```python
data = {
    'license_plate': 'T61 1679',
    'direction': 'IN',
    'vehicle_weight': 1.5,
    'device_id': 'RASPBERRY_PI_001',
    'api_key': 'raspberry_pi_key_123',
    'image_path': 'https://i.ibb.co/xxxxx/image.jpg'
}

POST /api/upload → Server lưu vào database
```

---

## ⏱️ TIMEOUT & XỬ LÝ LỖI

### **Timeout:**
- Nếu sau `SCAN_TIMEOUT` (10 giây) không tìm thấy biển số:
  - Upload với biển số = `"UNKNOWN"`
  - Vẫn lưu ảnh để kiểm tra sau

### **Fallback:**
- Nếu PaddleOCR lỗi → dùng EasyOCR
- Nếu EasyOCR lỗi → dùng DTK LPR SDK
- Nếu tất cả lỗi → return `None`

---

## 🎯 TÓM TẮT FLOW HOÀN CHỈNH

```
1. Camera chụp ảnh liên tục
   ↓
2. ESP32 phát hiện vật trên cân (≥30g)
   ↓
3. Kích hoạt scan_trigger = True
   ↓
4. Chụp ảnh mới từ camera
   ↓
5. PaddleOCR đọc tất cả text
   ↓
6. Lọc text (bỏ "THACO", "FORLAND", ...)
   ↓
7. Kiểm tra format biển số VN
   ↓
8. Ghép text nếu bị tách ("T61" + "1679")
   ↓
9. Chọn biển số tốt nhất
   ↓
10. Upload ảnh lên ImgBB
   ↓
11. Gửi dữ liệu lên server
   ↓
12. Hoàn tất! ✅
```

---

## 🔧 CẤU HÌNH QUAN TRỌNG

```python
MIN_WEIGHT_KG = 0.03      # Trọng lượng tối thiểu (30g)
SCAN_TIMEOUT = 10         # Thời gian chờ tối đa (10 giây)
DTK_LPR_ENABLED = False   # Bật DTK LPR SDK nếu có
```

---

## 💡 LƯU Ý

1. **Thread-safe:** Dùng `frame_lock` để tránh race condition
2. **Error handling:** Mọi lỗi đều được catch và log
3. **Fallback:** Luôn có phương án dự phòng
4. **Performance:** Chỉ quét khi có vật trên cân (tiết kiệm CPU)

