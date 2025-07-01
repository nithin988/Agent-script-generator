# Agent Script Interface Module

Transform your mindmaps and PDFs into structured agent workflows using a modern web interface and Python backend.

## Features
- Upload PDF mindmaps and extract structured workflows as JSON
- Modern, responsive web UI
- Fallback mode if Mistral/Ollama is not available
- All processing runs locally

## Requirements
- Python 3.8+
- pip
- (Optional) Mistral/Ollama running on `localhost:11434` for advanced JSON extraction

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-username/your-repo-name.git
   cd agent-script-interface
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **(Optional) Start Mistral/Ollama:**
   - Download and run Ollama from https://ollama.ai
   - Pull the Mistral model: `ollama pull mistral`
   - Start Ollama: `ollama run mistral`


5. **Start the application:**
   ```sh
   python app.py
   # or use the startup script for auto-setup:
   python run.py
   ```

6. **Open your browser and go to:**
   [http://localhost:5000](http://localhost:5000)

## Usage
- Drag and drop a PDF mindmap or use the file picker.
- Click "Process Document" to extract and generate the agent workflow JSON.
- Download the generated JSON for use in your projects.


## Project Structure
- `app.py` — Flask backend for file upload and processing
- `index.html` — Web frontend
- `requirements.txt` — Python dependencies
- `run.py` — Automated setup and launch script
- `outputs/` — Generated output files
- `static/` — Static files (e.g., images like kimaru-logo.png)
## Serving Images and Static Files

Place any images (such as `kimaru-logo.png`) in a folder named `static` in your project root. Reference them in your HTML as `static/kimaru-logo.png`. Flask will serve these files automatically at `/static/filename`.

Example:
```html
<img src="static/kimaru-logo.png" alt="Kimaru Logo" />
```

## Deployment on Render

1. Push your project to a GitHub (or GitLab/Bitbucket) repository.
2. Add a `Procfile` to your project root with this content:
   ```
   web: gunicorn app:app
   ```
3. On the [Render dashboard](https://dashboard.render.com/), create a new Web Service and connect your repository.
4. Set the build command to `pip install -r requirements.txt` and the start command to `gunicorn app:app`.
5. Deploy!

**Note:** If you use the `if __name__ == "__main__":` block in `app.py`, Render will ignore it and use Gunicorn to serve your app.

## Troubleshooting
- If you see a white screen, check the terminal for errors and ensure `index.html` is present.
- If you get connection errors, make sure the server is running and you are visiting the correct port.
- For PDF extraction issues, ensure your PDF is not encrypted and is structured as a mindmap.

## License
MIT
