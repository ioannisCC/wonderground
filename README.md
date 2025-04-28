# Image Generator Web App

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

### 5. Run the application

```bash
python app.py
```

The application will be available at http://localhost:5000