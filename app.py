from flask import Flask, redirect, url_for, session, render_template, flash, request
from flask_dance.contrib.google import make_google_blueprint, google
from functools import wraps
from dotenv import load_dotenv
import os
import secrets
import datetime
import base64
from openai import OpenAI
import tempfile
import pyheif
from PIL import Image
import io
import logging
from logging.handlers import RotatingFileHandler
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables
load_dotenv()

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

# Create app
app = Flask(__name__, static_url_path='/assets', static_folder='assets')

# Add file handler to app logger
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Application startup')

# Security configurations
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    app.logger.error("No SECRET_KEY set! Using a random secret key.")
    app.secret_key = secrets.token_hex(32)  # Stronger key for production

# Google OAuth configuration
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

# Force HTTPS in production
app.config["PREFERRED_URL_SCHEME"] = "https"

# Enforce HTTPS with Talisman
csp = {
    'default-src': '\'self\'',
    'img-src': ['\'self\'', 'data:', 'https://lh3.googleusercontent.com'],
    'script-src': ['\'self\'', '\'unsafe-inline\''],  # Modify as needed
    'style-src': ['\'self\'', '\'unsafe-inline\'']    # Modify as needed
}
talisman = Talisman(
    app,
    content_security_policy=csp,
    content_security_policy_nonce_in=['script-src', 'style-src'],
    force_https=os.environ.get("ENVIRONMENT") == "production",
    strict_transport_security=True,
    strict_transport_security_preload=True,
    session_cookie_secure=os.environ.get("ENVIRONMENT") == "production",
    session_cookie_http_only=True
)

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Company email domain for authentication
COMPANY_DOMAIN = os.environ.get("COMPANY_DOMAIN", "viralpassion.gr")

# Valid image sizes for gpt-image-1
VALID_SIZES = ["1024x1024", "1536x1024", "1024x1536", "auto"]

# Create the Google OAuth blueprint
google_bp = make_google_blueprint(
    scope=["profile", "email"],
    redirect_to="google_callback"
)
app.register_blueprint(google_bp, url_prefix="/login")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    # Show error message if present
    error = request.args.get('error')
    # If already logged in, redirect to home
    if session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/login/google/callback')
def google_callback():
    if not google.authorized:
        app.logger.warning("Authentication failed - not authorized")
        flash("Authentication failed. Please try again.")
        return redirect(url_for('login', error="Authentication failed"))
    
    try:
        resp = google.get("/oauth2/v1/userinfo")
        if not resp.ok:
            app.logger.error(f"Failed to get user info: {resp.text}")
            return redirect(url_for('login', error="Failed to get user information"))
        
        user_info = resp.json()
        email = user_info.get('email', '')
        
        # Check if user's email belongs to the company domain
        if not email.endswith(f"@{COMPANY_DOMAIN}"):
            app.logger.warning(f"Unauthorized login attempt with email: {email}")
            # Clear the OAuth token
            token = google_bp.token
            if token:
                del token
            return redirect(url_for('login', error=f"Please use your @{COMPANY_DOMAIN} email to login"))
        
        # Authentication successful
        session['authenticated'] = True
        session['email'] = email
        session['name'] = user_info.get('name', '')
        session['picture'] = user_info.get('picture', '')
        session.permanent = True
        app.permanent_session_lifetime = datetime.timedelta(hours=8)
        
        app.logger.info(f"User logged in: {email}")
        return redirect(url_for('index'))
        
    except Exception as e:
        app.logger.error(f"Error during authentication: {str(e)}")
        return redirect(url_for('login', error="An error occurred during authentication"))

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    return redirect(url_for('login'))

@app.route('/generate', methods=['POST'])
@login_required
@limiter.limit("20 per hour")  # Rate limit for image generation
def generate_image():
    # Check if we're dealing with a form submission with files
    is_form_data = request.content_type and 'multipart/form-data' in request.content_type
    has_files = False
    
    if is_form_data:
        for key in request.files:
            if request.files[key].filename:
                has_files = True
                break
    
    # Get common parameters
    if is_form_data:
        prompt = request.form.get('prompt', '')
        size = request.form.get('size', '1024x1024')
    else:
        data = request.json or {}
        prompt = data.get('prompt', '')
        size = data.get('size', '1024x1024')
    
    # Validate prompt
    if not prompt:
        return {'error': 'Prompt is required'}, 400
    
    # Validate size
    if size not in VALID_SIZES:
        return {'error': f'Invalid size. Choose from: {", ".join(VALID_SIZES)}'}, 400
    
    try:
        if is_form_data and has_files:
            # Process form data with images (use edit endpoint)
            # Collect all image files from the request
            image_files = []
            for key in request.files:
                file = request.files[key]
                if file.filename:
                    # Check file extension to make sure it's supported
                    ext = os.path.splitext(file.filename)[1].lower()
                    
                    # Check file size (25MB = 25 * 1024 * 1024 bytes)
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)  # Reset file pointer to beginning
                    
                    if file_size > 25 * 1024 * 1024:
                        return {'error': f'File {file.filename} exceeds the 25MB size limit.'}, 400
                    
                    if ext in ['.png', '.jpg', '.jpeg', '.webp', '.heic']:
                        image_files.append(file)
            
            if not image_files:
                return {'error': 'No supported image files uploaded. Please use PNG, JPG, JPEG, WEBP, or HEIC.'}, 400
            
            # Save the files temporarily as the OpenAI API needs file objects
            temp_files = []
            image_file_objects = []
            
            try:
                for image_file in image_files:
                    # Get file extension
                    filename = image_file.filename
                    ext = os.path.splitext(filename)[1].lower()
                    
                    # Create a temporary file
                    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    
                    # If HEIC, convert to PNG
                    if ext == '.heic':
                        # Read HEIC file
                        heif_file = pyheif.read(image_file.read())
                        
                        # Convert to PIL Image
                        image = Image.frombytes(
                            heif_file.mode, 
                            heif_file.size, 
                            heif_file.data,
                            "raw",
                            heif_file.mode,
                            heif_file.stride,
                        )
                        
                        # Save as PNG
                        image.save(temp.name, format="PNG")
                    else:
                        # For other formats, just save the file
                        image_file.save(temp.name)
                    
                    temp.close()
                    temp_files.append(temp.name)
                
                # Open all the files for the API
                image_file_objects = [open(file, 'rb') for file in temp_files]
                
                # For multiple images with gpt-image-1, we use an array
                # For a single image, we still use an array to maintain consistency
                image_param = image_file_objects
                
                result = client.images.edit(
                    model="gpt-image-1",
                    image=image_param,
                    prompt=prompt,
                    size=size,
                    quality="high",
                )
                
                image_base64 = result.data[0].b64_json
                
                return {'success': True, 'image': image_base64}
            finally:
                # Ensure cleanup happens regardless of success or failure
                # Close all file handles
                for file_obj in image_file_objects:
                    file_obj.close()
                    
                # Delete all temp files
                for file_path in temp_files:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                
        else:
            # No images, just a prompt (use generate endpoint)
            result = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size=size,
                quality="high",
                output_format="png",
                moderation="low",
            )
            
            image_base64 = result.data[0].b64_json
            
            return {'success': True, 'image': image_base64}
    except Exception as e:
        app.logger.error(f"Error generating image: {str(e)}")
        return {'error': str(e)}, 500

# Global error handler
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    return {'error': 'An unexpected error occurred'}, 500

# For development only - in production, use a proper WSGI server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)