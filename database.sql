-- ============================================================
-- HỆ THỐNG KIỂM SOÁT XE RA VÀO - MySQL Database
-- ============================================================
-- Hướng dẫn: Copy toàn bộ đoạn code dưới và paste vào phpMyAdmin

-- Bước 1: Chọn database esp32_data (đã tồn tại)
USE esp32_data;

-- Bước 2: Tạo bảng lưu thông tin xe ra vào
CREATE TABLE IF NOT EXISTS vehicle_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID tự động tăng',
    license_plate VARCHAR(20) NOT NULL COMMENT 'Biển số xe',
    direction VARCHAR(10) NOT NULL COMMENT 'Hướng: IN (vào) hoặc OUT (ra)',
    vehicle_weight DECIMAL(10, 2) DEFAULT NULL COMMENT 'Trọng lượng xe (tấn)',
    capture_time DATETIME NOT NULL COMMENT 'Thời gian chụp ảnh/ghi nhận',
    image_path VARCHAR(255) DEFAULT NULL COMMENT 'Đường dẫn ảnh xe',
    device_id VARCHAR(50) DEFAULT NULL COMMENT 'ID thiết bị (camera/cân)',
    notes TEXT COMMENT 'Ghi chú thêm',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian tạo record',
    
    -- Tạo chỉ mục để tìm kiếm nhanh
    INDEX idx_license_plate (license_plate),
    INDEX idx_capture_time (capture_time),
    INDEX idx_direction (direction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Bảng lưu thông tin xe vào/ra và trọng lượng';

-- ============================================================
-- DỮ LIỆU MẪU ĐỂ TEST (Tùy chọn - có thể bỏ qua)
-- ============================================================
INSERT INTO vehicle_records (license_plate, direction, vehicle_weight, capture_time, device_id, notes) VALUES
('29A-12345', 'IN', 5.5, '2024-01-15 08:30:00', 'CAMERA_001', 'Xe tải vào'),
('30B-67890', 'IN', 3.2, '2024-01-15 09:15:00', 'CAMERA_001', 'Xe con vào'),
('29A-12345', 'OUT', 5.8, '2024-01-15 10:45:00', 'CAMERA_001', 'Xe tải ra'),
('43C-11111', 'IN', 2.1, '2024-01-15 11:30:00', 'CAMERA_001', 'Xe máy vào'),
('30B-67890', 'OUT', 3.5, '2024-01-15 14:20:00', 'CAMERA_001', 'Xe con ra');

-- ============================================================
-- KẾT THÚC - Bạn đã tạo xong bảng!
-- ============================================================
-- Để xem bảng vừa tạo: Click vào database esp32_data → Tab "Structure"
-- Để xem dữ liệu: Click vào bảng vehicle_records → Tab "Browse"

