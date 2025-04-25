# Elegant Image Generator Web App

A simple, elegant web application for generating images using OpenAI's image generation API.

## Features

- Clean, minimalist interface
- Text prompt input for image generation
- One-click image download
- Responsive design that works on mobile and desktop

## Setup Instructions

### 1. Clone or download this repository

Place all files in a directory of your choice.

### 2. Create a virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your OpenAI API key

Create a `.env` file in the root directory with your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

You can get your API key from the [OpenAI dashboard](https://platform.openai.com/account/api-keys).

### 5. Create a templates folder

Create a folder named `templates` in the root directory and place the `index.html` file inside it.

```
mkdir templates
mv index.html templates/
```

### 6. Run the application

```bash
python app.py
```

The application will be available at http://localhost:5000

## Usage

1. Enter your prompt in the text area
2. Click "Generate Image"
3. Wait for the image to be generated
4. Click "Download Image" to save the image to your device

## Deployment Options

For production deployment, consider these options:

### 1. Render

Render offers a free tier that works well for simple Flask applications.

### 2. Heroku

Heroku is another good option that offers free and paid tiers.

### 3. PythonAnywhere

PythonAnywhere is a Python-specific hosting service that's easy to set up.

### 4. AWS, Google Cloud, or Azure

For more scalable options, consider major cloud providers.

## Important Notes

- Make sure your OpenAI API key is kept secret and not exposed in your code
- The OpenAI API is not free, so you will incur charges for generating images
- The web app is set to generate 1024x1024 images with high quality, which may affect API costs

## Customization

- Edit the CSS in the `<style>` section of `index.html` to change colors and layout
- Modify the prompt textarea's default value in the JavaScript section
- Adjust image generation parameters in the Python code for different sizes or quality