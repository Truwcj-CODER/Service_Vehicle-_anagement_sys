#!/usr/bin/env python3
"""
Script để xóa tất cả dữ liệu cũ từ bảng vehicle_records
"""

import mysql.connector
from mysql.connector import Error
from config import Config

def clear_database():
    """Xóa tất cả dữ liệu từ bảng vehicle_records"""
    try:
        # Kết nối tới MySQL
        print("🔗 Đang kết nối tới MySQL...")
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE
        )
        
        if not connection.is_connected():
            print("❌ Không thể kết nối tới MySQL!")
            return False
        
        print("✅ Kết nối thành công!")
        
        cursor = connection.cursor()
        
        # Xóa tất cả dữ liệu
        print("\n🗑️  Đang xóa tất cả dữ liệu từ bảng vehicle_records...")
        cursor.execute("DELETE FROM vehicle_records")
        connection.commit()
        
        # Lấy số hàng bị xóa
        deleted_rows = cursor.rowcount
        
        # Reset auto_increment
        print("🔄 Đang reset Auto Increment...")
        cursor.execute("ALTER TABLE vehicle_records AUTO_INCREMENT = 1")
        connection.commit()
        
        cursor.close()
        connection.close()
        
        print(f"✅ Xóa thành công! Đã xóa {deleted_rows} record(s)")
        print("🔄 Auto Increment đã được reset về 1")
        return True
        
    except Error as e:
        print(f"❌ Lỗi MySQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("   XÓA DỮ LIỆU CŨ TỪ DATABASE")
    print("=" * 50)
    
    # Xác nhận trước khi xóa
    confirm = input("\n⚠️  Bạn chắc chắn muốn xóa TẤT CẢ dữ liệu? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        clear_database()
        print("\n✨ Xong! Database sẵn sàng cho dữ liệu mới.\n")
    else:
        print("❌ Hủy bỏ.\n")
