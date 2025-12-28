/*
 * ESP32 - Upload ảnh và dữ liệu lên server
 * Hệ thống: Kiểm soát xe ra vào
 * 
 * Thư viện cần cài:
 * - WiFi (built-in)
 * - HTTPClient (built-in)
 * - ArduinoJson (Library Manager)
 * - Camera (tùy chọn, nếu dùng ESP32-CAM)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"  // Chỉ cho ESP32-CAM

// ==================== CẤU HÌNH WIFI ====================
const char* ssid = "TEN_WIFI_CUA_BAN";
const char* password = "MAT_KHAU_WIFI";

// ==================== CẤU HÌNH SERVER ====================
const char* SERVER_URL = "http://192.168.1.100:5000/api/upload";  // Địa chỉ IP server
const char* API_KEY = "raspberry_pi_key_123";  // API key (phải khớp với server)

// ==================== CẤU HÌNH CAMERA (ESP32-CAM) ====================
#define CAMERA_MODEL_AI_THINKER  // Hoặc CAMERA_MODEL_ESP32S3_EYE, etc.
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ==================== BIẾN TOÀN CỤC ====================
String device_id = "ESP32_CAM_001";

// ==================== HÀM KẾT NỐI WIFI ====================
void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.println("WiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// ==================== HÀM KHỞI TẠO CAMERA ====================
void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // Chất lượng ảnh (0-63, càng nhỏ càng chất lượng cao)
  if(psramFound()){
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }
  
  // Khởi tạo camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
  
  Serial.println("Camera initialized!");
}

// ==================== HÀM CHỤP ẢNH ====================
camera_fb_t* capturePhoto() {
  Serial.println("Capturing photo...");
  
  // Chụp ảnh
  camera_fb_t *fb = esp_camera_fb_get();
  
  if (!fb) {
    Serial.println("Camera capture failed");
    return NULL;
  }
  
  Serial.printf("Picture taken! Size: %d bytes\n", fb->len);
  return fb;
}

// ==================== HÀM CHUYỂN ĐỔI SANG BASE64 ====================
String imageToBase64(uint8_t* buffer, size_t length) {
  const char base64_chars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  String encoded = "";
  int i = 0;
  int j = 0;
  uint8_t char_array_3[3];
  uint8_t char_array_4[4];
  
  while (length--) {
    char_array_3[i++] = *(buffer++);
    if (i == 3) {
      char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
      char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
      char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
      char_array_4[3] = char_array_3[2] & 0x3f;
      
      for(i = 0; i < 4; i++) {
        encoded += base64_chars[char_array_4[i]];
      }
      i = 0;
    }
  }
  
  if (i) {
    for(j = i; j < 3; j++) {
      char_array_3[j] = '\0';
    }
    
    char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
    char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
    char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
    
    for (j = 0; j < i + 1; j++) {
      encoded += base64_chars[char_array_4[j]];
    }
    
    while((i++ < 3)) {
      encoded += '=';
    }
  }
  
  return encoded;
}

// ==================== HÀM GỬI DỮ LIỆU LÊN SERVER ====================
bool uploadToServer(String licensePlate, String direction, float weight, camera_fb_t* fb) {
  if (!fb) {
    Serial.println("No image to upload");
    return false;
  }
  
  Serial.println("Preparing JSON...");
  
  // Tạo JSON payload
  DynamicJsonDocument doc(50000);  // Kích thước lớn để chứa base64 image
  doc["license_plate"] = licensePlate;
  doc["direction"] = direction;
  doc["vehicle_weight"] = weight;
  doc["device_id"] = device_id;
  doc["notes"] = "Uploaded from ESP32-CAM";
  doc["api_key"] = API_KEY;
  
  // Chuyển ảnh sang base64
  String imageBase64 = imageToBase64(fb->buf, fb->len);
  doc["image_base64"] = imageBase64;
  
  // Serialize JSON
  String jsonPayload;
  serializeJson(doc, jsonPayload);
  
  Serial.printf("JSON size: %d bytes\n", jsonPayload.length());
  
  // Gửi HTTP POST
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  
  Serial.println("Sending to server...");
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    Serial.printf("Response code: %d\n", httpResponseCode);
    String response = http.getString();
    Serial.println("Response:");
    Serial.println(response);
    
    http.end();
    
    // Giải phóng buffer ảnh
    esp_camera_fb_return(fb);
    
    return (httpResponseCode == 200);
  } else {
    Serial.printf("Error: %s\n", http.errorToString(httpResponseCode).c_str());
    http.end();
    esp_camera_fb_return(fb);
    return false;
  }
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n===================================");
  Serial.println("ESP32 Vehicle Detection System");
  Serial.println("===================================\n");
  
  // Kết nối WiFi
  connectWiFi();
  
  // Khởi tạo camera
  initCamera();
  
  Serial.println("\nSystem ready! Waiting for trigger...");
}

// ==================== LOOP ====================
void loop() {
  // Ví dụ: Trigger khi có cảm biến phát hiện xe
  // Hoặc có thể dùng button, timer, v.v.
  
  // Đợi 10 giây (hoặc thay bằng trigger thực tế)
  delay(10000);
  
  Serial.println("\n--- Trigger detected ---");
  
  // Giả lập dữ liệu (thay bằng cảm biến thực tế)
  String licensePlate = "29A-12345";  // Hoặc nhận diện từ OCR
  String direction = "IN";           // "IN" hoặc "OUT"
  float weight = 5.5;                 // Từ cảm biến cân
  
  // Chụp ảnh
  camera_fb_t* fb = capturePhoto();
  
  // Gửi lên server
  bool success = uploadToServer(licensePlate, direction, weight, fb);
  
  if (success) {
    Serial.println("✅ Upload successful!");
  } else {
    Serial.println("❌ Upload failed!");
  }
  
  Serial.println("Waiting for next trigger...\n");
}

