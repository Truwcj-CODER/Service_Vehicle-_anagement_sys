from fastapi import FastAPI, HTTPException, Query, Depends, status, File, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from config import Config

# Khởi tạo FastAPI app
app = FastAPI(
    title="Hệ Thống Quản Lý Thiết Bị",
    description="Quản lý thông tin thiết bị từ MySQL database",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security settings
SECRET_KEY = "your-secret-key-change-in-production-change-this-to-a-random-string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Default admin user (change this in production!)
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "1"

# Mount static files
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount templates
if os.path.exists("templates"):
    app.mount("/static", StaticFiles(directory="templates"), name="static")

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str

class DeviceRecord(BaseModel):
    license_plate: str
    direction: str  # "IN" (vào) hoặc "OUT" (ra)
    vehicle_weight: Optional[float] = None
    capture_time: datetime
    image_path: Optional[str] = None
    device_id: Optional[str] = None
    notes: Optional[str] = None

class DeviceRecordResponse(BaseModel):
    id: int
    license_plate: str
    direction: str
    vehicle_weight: Optional[float]
    capture_time: str
    image_path: Optional[str]
    device_id: Optional[str]
    notes: Optional[str]
    created_at: str

class StatsResponse(BaseModel):
    total_records: int
    unique_plates: int
    today_records: int
    today_in: int  # Số xe vào hôm nay
    today_out: int  # Số xe ra hôm nay
    total_weight: float

# Authentication functions
def verify_password(plain_password, hashed_password):
    """Verify a password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Database connection helper
def get_db_connection():
    """Create and return MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Public routes
@app.post("/api/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Login endpoint"""
    # Simple authentication (change this in production!)
    if login_data.username == DEFAULT_USERNAME and login_data.password == DEFAULT_PASSWORD:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": login_data.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Login page"""
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Đăng Nhập - Hệ Thống Quản Lý Thiết Bị</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #145a32 0%, #1e8449 50%, #27ae60 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: 'Inter', sans-serif;
            }
            .login-box {
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 50px rgba(0,0,0,0.3);
                padding: 50px;
                max-width: 450px;
                width: 100%;
            }
            .login-box h2 {
                color: #2c3e50;
                font-weight: 700;
                margin-bottom: 30px;
            }
            .btn-login {
                background: linear-gradient(135deg, #145a32 0%, #1e8449 100%);
                border: none;
                padding: 12px;
                font-weight: 600;
                border-radius: 10px;
            }
            .btn-login:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(20, 90, 50, 0.4);
            }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>🔐 Đăng Nhập</h2>
            <form id="loginForm">
                <div class="mb-3">
                    <label class="form-label">Tên đăng nhập</label>
                    <input type="text" class="form-control" id="username" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Mật khẩu</label>
                    <input type="password" class="form-control" id="password" required>
                </div>
                <button type="submit" class="btn btn-primary btn-login w-100">Đăng Nhập</button>
            </form>
            <div id="errorMsg" class="alert alert-danger mt-3" style="display:none;"></div>
        </div>
        <script>
            document.getElementById('loginForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                try {
                    const response = await fetch('/api/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password})
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        localStorage.setItem('access_token', data.access_token);
                        window.location.href = '/dashboard';
                    } else {
                        document.getElementById('errorMsg').style.display = 'block';
                        document.getElementById('errorMsg').textContent = 'Sai tên đăng nhập hoặc mật khẩu';
                    }
                } catch (error) {
                    document.getElementById('errorMsg').style.display = 'block';
                    document.getElementById('errorMsg').textContent = 'Lỗi kết nối';
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Dashboard page (protected)"""
    # Check if token exists in localStorage
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), headers={"Content-Type": "text/html; charset=utf-8"})
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Template file not found</h1><p><a href='/login'>Go to login</a></p>", headers={"Content-Type": "text/html; charset=utf-8"})

@app.get("/")
async def root():
    """Redirect to login if not authenticated"""
    return RedirectResponse(url="/login")

# Protected routes
@app.get("/api/records")
async def get_records(
    date: Optional[str] = Query(None),
    license_plate: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    sort: Optional[str] = Query("time_desc"),
    weight_min: Optional[float] = Query(None),
    weight_max: Optional[float] = Query(None),
    limit: Optional[int] = Query(None),
    current_user: str = Depends(verify_token)
):
    """Get device records with optional filters - Protected"""
    try:
        connection = get_db_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT * FROM vehicle_records WHERE 1=1"
        params = []
        
        if date:
            query += " AND DATE(capture_time) = %s"
            params.append(date)
        
        if license_plate:
            query += " AND license_plate LIKE %s"
            params.append(f"%{license_plate}%")
        
        if direction:
            query += " AND direction = %s"
            params.append(direction)
        
        if weight_min is not None:
            query += " AND vehicle_weight >= %s"
            params.append(weight_min)
        
        if weight_max is not None:
            query += " AND vehicle_weight <= %s"
            params.append(weight_max)
        
        # Sắp xếp
        if sort == "time_asc":
            query += " ORDER BY capture_time ASC"
        elif sort == "time_desc":
            query += " ORDER BY capture_time DESC"
        elif sort == "weight_desc":
            query += " ORDER BY vehicle_weight DESC"
        elif sort == "weight_asc":
            query += " ORDER BY vehicle_weight ASC"
        elif sort == "plate_asc":
            query += " ORDER BY license_plate ASC"
        elif sort == "plate_desc":
            query += " ORDER BY license_plate DESC"
        else:
            query += " ORDER BY capture_time DESC"
        
        # Giới hạn số lượng
        if limit:
            limit_value = int(limit)
            if limit_value > 0 and limit_value <= 1000:  # Giới hạn tối đa 1000
                query += " LIMIT %s"
                params.append(limit_value)
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        for record in records:
            if record.get('capture_time'):
                record['capture_time'] = record['capture_time'].isoformat()
            if record.get('created_at'):
                record['created_at'] = record['created_at'].isoformat()
            if record.get('vehicle_weight') is not None:
                record['vehicle_weight'] = float(record['vehicle_weight'])
        
        return records
    
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(current_user: str = Depends(verify_token)):
    """Get statistics about records - Protected"""
    try:
        connection = get_db_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total FROM vehicle_records")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(DISTINCT license_plate) as unique_plates FROM vehicle_records")
        unique_plates = cursor.fetchone()['unique_plates']
        
        cursor.execute("SELECT COUNT(*) as today FROM vehicle_records WHERE DATE(capture_time) = CURDATE()")
        today = cursor.fetchone()['today']
        
        cursor.execute("SELECT COUNT(*) as today_in FROM vehicle_records WHERE DATE(capture_time) = CURDATE() AND direction = 'IN'")
        today_in = cursor.fetchone()['today_in']
        
        cursor.execute("SELECT COUNT(*) as today_out FROM vehicle_records WHERE DATE(capture_time) = CURDATE() AND direction = 'OUT'")
        today_out = cursor.fetchone()['today_out']
        
        cursor.execute("SELECT COALESCE(SUM(vehicle_weight), 0) as total_weight FROM vehicle_records")
        total_weight = float(cursor.fetchone()['total_weight'])
        
        cursor.close()
        connection.close()
        
        return StatsResponse(
            total_records=total,
            unique_plates=unique_plates,
            today_records=today,
            today_in=today_in,
            today_out=today_out,
            total_weight=total_weight
        )
    
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/record")
async def add_record(record: DeviceRecord, current_user: str = Depends(verify_token)):
    """Add a new device record - Protected"""
    try:
        connection = get_db_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor()
        query = """INSERT INTO vehicle_records 
                   (license_plate, direction, vehicle_weight, capture_time, image_path, device_id, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(query, (
            record.license_plate,
            record.direction,
            record.vehicle_weight,
            record.capture_time,
            record.image_path,
            record.device_id,
            record.notes
        ))
        
        connection.commit()
        record_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return {"success": True, "id": record_id}
    
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

class DeviceUploadRequest(BaseModel):
    license_plate: str
    direction: str = "IN"  # Mặc định là "IN" (vào), có thể là "OUT" (ra)
    vehicle_weight: Optional[float] = None
    device_id: Optional[str] = None
    image_base64: Optional[str] = None
    image_path: Optional[str] = None  # URL ảnh từ ImgBB hoặc đường dẫn khác
    notes: Optional[str] = None
    api_key: str

@app.post("/api/upload")
async def upload_device_data(request: DeviceUploadRequest):
    """
    Upload device data from Raspberry Pi - Public endpoint with API key protection
    API Key: raspberry_pi_key_123 (change in production!)
    """
    # Simple API key check
    if request.api_key != "raspberry_pi_key_123":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        import base64
        from datetime import datetime
        
        # Generate image path
        now = datetime.now()
        
        # Nếu có image_path từ request (URL từ ImgBB), dùng nó
        # Nếu không, mới tạo đường dẫn local và lưu file
        if request.image_path:
            image_path = request.image_path
        else:
            date_str = now.strftime("%Y/%m/%d")
            time_str = now.strftime("%H%M%S")
            safe_plate = request.license_plate.replace('-', '_')
            image_filename = f"{safe_plate}_{now.strftime('%Y%m%d')}_{time_str}.jpg"
            image_path = f"/uploads/{date_str}/{image_filename}"
            
            # Save image if provided
            if request.image_base64:
                import os
                upload_dir = os.path.join("uploads", date_str)
                os.makedirs(upload_dir, exist_ok=True)
                
                image_data = base64.b64decode(request.image_base64)
                with open(os.path.join(upload_dir, image_filename), 'wb') as f:
                    f.write(image_data)
        
        # Insert into database
        connection = get_db_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor()
        query = """INSERT INTO vehicle_records 
                   (license_plate, direction, vehicle_weight, capture_time, image_path, device_id, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(query, (
            request.license_plate,
            request.direction,
            request.vehicle_weight,
            now,
            image_path,
            request.device_id,
            request.notes
        ))
        
        connection.commit()
        record_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return {
            "success": True,
            "id": record_id,
            "message": "Data uploaded successfully",
            "capture_time": now.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-image")
async def upload_image_file(
    license_plate: str = Form(...),
    direction: str = Form("IN"),
    vehicle_weight: Optional[float] = Form(None),
    device_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    api_key: str = Form(...),
    image: Optional[UploadFile] = File(None),
    image_path: Optional[str] = Form(None)  # URL từ ImgBB
):
    """
    Upload ảnh trực tiếp từ Raspberry Pi (multipart/form-data)
    Dễ dùng hơn cho USB camera trên Raspberry Pi
    API Key: raspberry_pi_key_123 (change in production!)
    
    Example:
        curl -X POST "http://localhost:5000/api/upload-image" \\
            -F "license_plate=29A-12345" \\
            -F "direction=IN" \\
            -F "vehicle_weight=5.5" \\
            -F "device_id=RASPBERRY_PI_001" \\
            -F "api_key=raspberry_pi_key_123" \\
            -F "image=@/path/to/image.jpg"
    """
    # Simple API key check
    if api_key != "raspberry_pi_key_123":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        now = datetime.now()
        
        # Nếu có image_path từ request (URL từ ImgBB), dùng nó
        # Nếu không, mới validate và lưu file local
        if image_path:
            # Dùng URL từ ImgBB hoặc đường dẫn khác
            final_image_path = image_path
        elif image:
            # Validate image file
            if not image.content_type or not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Generate image path
            date_str = now.strftime("%Y/%m/%d")
            time_str = now.strftime("%H%M%S")
            safe_plate = license_plate.replace('-', '_').replace(' ', '_')
            
            # Get file extension from original filename or default to jpg
            file_ext = os.path.splitext(image.filename)[1] if image.filename else '.jpg'
            if not file_ext:
                file_ext = '.jpg'
            
            image_filename = f"{safe_plate}_{now.strftime('%Y%m%d')}_{time_str}{file_ext}"
            final_image_path = f"/uploads/{date_str}/{image_filename}"
            
            # Create upload directory
            upload_dir = os.path.join("uploads", date_str)
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save image file
            file_path = os.path.join(upload_dir, image_filename)
            with open(file_path, 'wb') as f:
                content = await image.read()
                f.write(content)
        else:
            raise HTTPException(status_code=400, detail="Either image file or image_path must be provided")
        
        # Insert into database
        connection = get_db_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor()
        query = """INSERT INTO vehicle_records 
                   (license_plate, direction, vehicle_weight, capture_time, image_path, device_id, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(query, (
            license_plate,
            direction,
            vehicle_weight,
            now,
            final_image_path,
            device_id,
            notes
        ))
        
        connection.commit()
        record_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return {
            "success": True,
            "id": record_id,
            "message": "Image uploaded successfully",
            "image_path": final_image_path,
            "capture_time": now.isoformat(),
            "license_plate": license_plate
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    connection = get_db_connection()
    if connection:
        connection.close()
        return {"status": "healthy", "database": "connected"}
    return {"status": "unhealthy", "database": "disconnected"}

@app.get("/api/logout")
async def logout():
    """Logout endpoint"""
    return {"message": "Logged out successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
