from flask import Flask, render_template, request, jsonify
import base64
from openai import OpenAI
import os
from dotenv import load_dotenv

# load environment variables
load_dotenv()

app = Flask(__name__, static_url_path='/assets', static_folder='assets')
client = OpenAI()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    data = request.json
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    try:
        result = client.images.generate(
            model="gpt-image-1",
            size="1024x1024",
            quality="high",
            output_format="png",
            prompt=prompt,
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