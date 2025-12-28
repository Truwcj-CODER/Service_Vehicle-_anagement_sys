#!/usr/bin/env python3
"""
Script để xem dữ liệu trong MySQL database
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime
import sys

def get_db_connection():
    """Tạo kết nối đến MySQL"""
    try:
        from config import Config
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE
        )
        return connection
    except Error as e:
        print(f"❌ Lỗi kết nối MySQL: {e}")
        return None

def view_all_records():
    """Xem tất cả records"""
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vehicle_records ORDER BY capture_time DESC")
        records = cursor.fetchall()
        
        if not records:
            print("\n📭 Chưa có dữ liệu")
            print("   Chạy: mysql -u root -p < database.sql")
            return
        
        print("\n" + "="*100)
        print("📊 TẤT CẢ DỮ LIỆU TRONG DATABASE")
        print("="*100 + "\n")
        
        for idx, record in enumerate(records, 1):
            print(f"🔹 Record #{idx} (ID: {record['id']})")
            print(f"   📅 Ngày giờ: {record['capture_time']}")
            print(f"   🚗 Biển số: {record['license_plate']}")
            direction_text = "👉 VÀO" if record.get('direction') == 'IN' else "👈 RA"
            print(f"   {direction_text}")
            print(f"   ⚖️  Khối lượng: {record['vehicle_weight'] if record['vehicle_weight'] else 'N/A'} tấn")
            print(f"   📷 Ảnh: {record.get('image_path', 'N/A')}")
            print(f"   🔧 Thiết bị: {record.get('device_id') or 'N/A'}")
            print(f"   ℹ️  Ghi chú: {record.get('notes') or 'N/A'}")
            print(f"   🕐 Tạo lúc: {record['created_at']}")
            print()
        
        print("="*100)
        print(f"✅ Tổng cộng: {len(records)} records")
        print("="*100)
        
    except Error as e:
        print(f"❌ Lỗi: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

def view_stats():
    """Xem thống kê"""
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Tổng records
        cursor.execute("SELECT COUNT(*) as total FROM vehicle_records")
        total = cursor.fetchone()['total']
        
        # Unique plates
        cursor.execute("SELECT COUNT(DISTINCT license_plate) as unique_plates FROM vehicle_records")
        unique_plates = cursor.fetchone()['unique_plates']
        
        # Total weight
        cursor.execute("SELECT COALESCE(SUM(vehicle_weight), 0) as total_weight FROM vehicle_records")
        total_weight = float(cursor.fetchone()['total_weight'])
        
        print("\n" + "="*50)
        print("📈 THỐNG KÊ")
        print("="*50)
        print(f"📊 Tổng số records: {total}")
        print(f"🚗 Số biển số khác nhau: {unique_plates}")
        print(f"⚖️  Tổng khối lượng: {total_weight:.2f} tấn")
        print("="*50 + "\n")
        
    except Error as e:
        print(f"❌ Lỗi: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

def view_by_plate(plate):
    """Xem theo biển số"""
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM vehicle_records WHERE license_plate = %s ORDER BY capture_time DESC",
            (plate,)
        )
        records = cursor.fetchall()
        
        if not records:
            print(f"\n❌ Không tìm thấy biển số: {plate}")
            return
        
        print(f"\n" + "="*80)
        print(f"🚗 BIỂN SỐ: {plate}")
        print("="*80 + "\n")
        
        total_weight = 0
        for idx, record in enumerate(records, 1):
            direction_text = "👉 VÀO" if record.get('direction') == 'IN' else "👈 RA"
            print(f"  #{idx}. {record['capture_time']} - {direction_text}")
            weight = record['vehicle_weight'] if record['vehicle_weight'] else 0
            print(f"     ⚖️  Khối lượng: {weight} tấn")
            if record.get('notes'):
                print(f"     ℹ️  {record['notes']}")
            print()
            total_weight += weight
        
        print(f"📊 Tổng số lần: {len(records)}")
        print(f"⚖️  Tổng khối lượng: {total_weight:.2f} tấn")
        print("="*80 + "\n")
        
    except Error as e:
        print(f"❌ Lỗi: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--stats":
            view_stats()
        elif sys.argv[1].startswith("--plate="):
            plate = sys.argv[1].replace("--plate=", "")
            view_by_plate(plate)
        else:
            print("Usage:")
            print("  python view_data.py          # Xem tất cả")
            print("  python view_data.py --stats  # Xem thống kê")
            print("  python view_data.py --plate=29A-12345  # Xem theo biển số")
    else:
        view_all_records()
        view_stats()

