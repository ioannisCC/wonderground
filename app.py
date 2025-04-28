from flask import Flask, render_template, request, jsonify
import base64
from openai import OpenAI
import os
import tempfile
from dotenv import load_dotenv
import pyheif
from PIL import Image
import io

# load environment variables
load_dotenv()

app = Flask(__name__, static_url_path='/assets', static_folder='assets')
client = OpenAI()

# Valid image sizes for gpt-image-1
VALID_SIZES = ["1024x1024", "1536x1024", "1024x1536", "auto"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
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
        return jsonify({'error': 'Prompt is required'}), 400
    
    # Validate size
    if size not in VALID_SIZES:
        return jsonify({
            'error': f'Invalid size. Choose from: {", ".join(VALID_SIZES)}'
        }), 400
    
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
                        return jsonify({
                            'error': f'File {file.filename} exceeds the 25MB size limit.'
                        }), 400
                    
                    if ext in ['.png', '.jpg', '.jpeg', '.webp', '.heic']:
                        image_files.append(file)
            
            if not image_files:
                return jsonify({'error': 'No supported image files uploaded. Please use PNG, JPG, JPEG, WEBP, or HEIC.'}), 400
            
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
                
                return jsonify({
                    'success': True,
                    'image': image_base64
                })
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
            
            return jsonify({
                'success': True,
                'image': image_base64
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)