from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import fitz  # PyMuPDF
import requests
import json
import os
import re
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyMuPDF"""
    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        blocks = page.get_text("blocks")
        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))  # sort top-to-bottom
        for block in sorted_blocks:
            text = block[4].strip()
            if text:
                # Split block text into individual lines
                block_lines = text.split('\n')
                for line in block_lines:
                    line = line.strip()
                    if line:
                        lines.append(line)
    
    # Format text with bullet points if not already present
    formatted_lines = []
    for line in lines:
        if not line.startswith('- '):
            formatted_lines.append(f"- {line}")
        else:
            formatted_lines.append(line)
    
    formatted_text = "\n".join(formatted_lines)
    doc.close()
    return formatted_text.strip()

def ask_mistral_agent(mindmap_text):
    """Send request to Mistral API"""
    prompt = f"""
You are a JSON-generating assistant that creates structured agent hierarchies with detailed descriptions.

Convert the following structured outline into a hierarchical JSON format with agents, subagents, descriptions, and actions.

Input format (text extracted from a PDF mindmap):
- 1. Load and Inspect Raw Data
- 1.1 Extract Data From Database
- 1.2 Import CSV Files
- 2. Clean Data
- 2.1 Remove Duplicates
- 2.2 Handle Missing Values

Expected JSON output format:
{{
  "agents": [
    {{
      "name": "Raw Data Handler Agent",
      "description": "Manages the initial acquisition and inspection of raw data from various sources.",
      "subagents": [
        {{
          "name": "Data Loader",
          "description": "Handles the extraction and import of data from databases and files.",
          "actions": [
            "Extract Data From Database",
            "Import CSV Files",
            "Validate data source connections"
          ]
        }}
      ]
    }},
    {{
      "name": "Data Cleaner Agent",
      "description": "Performs comprehensive data cleaning and quality assurance operations.",
      "subagents": [
        {{
          "name": "Data Processor",
          "description": "Removes inconsistencies and handles data quality issues.",
          "actions": [
            "Remove Duplicates",
            "Handle Missing Values",
            "Standardize data formats"
          ]
        }}
      ]
    }}
  ]
}}

Rules:
- Group related actions under meaningful agent names
- Create subagents that represent specialized roles
- Use descriptive agent names ending with "Agent"
- Use descriptive subagent names for specialized roles
- Include meaningful descriptions for both agents and subagents (1-2 sentences each)
- Group actions logically under appropriate subagents
- Return only raw JSON, no markdown or commentary

Now convert the following mindmap text into structured JSON:

{mindmap_text}
""".strip()

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['response']
        else:
            raise Exception(f"Mistral API error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        # Fallback: Generate a structured hierarchy based on the input
        return generate_structured_json(mindmap_text)
    except Exception as e:
        print(f"Error calling Mistral API: {e}")
        return generate_structured_json(mindmap_text)

def generate_structured_json(mindmap_text):
    """Generate a well-structured hierarchical JSON when Mistral is not available"""
    lines = [line.strip() for line in mindmap_text.split('\n') if line.strip()]
    
    # Parse the text to identify main topics and subtopics
    parsed_structure = []
    current_main = None
    
    for line in lines:
        if line.startswith('- '):
            line = line[2:]  # Remove '- ' prefix
        
        # Check if it's a main topic (numbered or major heading)
        if re.match(r'^\d+\.\s+', line) or is_main_topic(line):
            if current_main:
                parsed_structure.append(current_main)
            current_main = {
                'topic': line,
                'subtopics': []
            }
        else:
            # This is a subtopic/action
            if current_main:
                current_main['subtopics'].append(line)
            else:
                # Create a default main topic if none exists
                current_main = {
                    'topic': 'Base Processing Tasks',
                    'subtopics': [line]
                }
    
    # Don't forget the last main topic
    if current_main:
        parsed_structure.append(current_main)
    
    # Convert parsed structure to agent hierarchy
    agents = []
    
    for item in parsed_structure:
        topic = item['topic']
        subtopics = item['subtopics']
        
        # Generate agent name and description based on topic
        agent_name = generate_agent_name(topic)
        agent_description = generate_agent_description(topic)
        subagent_name = generate_subagent_name(topic)
        subagent_description = generate_subagent_description(topic)
        
        # Group actions intelligently
        agent = {
            "name": agent_name,
            "description": agent_description,
            "subagents": [{
                "name": subagent_name,
                "description": subagent_description,
                "actions": subtopics if subtopics else [topic]
            }]
        }
        
        agents.append(agent)
    
    # If no structure was found, create a comprehensive data processing structure
    if not agents:
        agents = create_default_structure(lines)
    
    result = {
        "agents": agents
    }
    
    return json.dumps(result, indent=2)

def is_main_topic(line):
    """Determine if a line represents a main topic"""
    # Look for keywords that indicate main topics
    main_topic_indicators = [
        'load', 'inspect', 'clean', 'handle', 'process', 'analyze', 
        'normalize', 'validate', 'convert', 'standardize', 'encode'
    ]
    
    line_lower = line.lower()
    
    # Check if line contains main topic indicators and doesn't look like a sub-action
    if any(indicator in line_lower for indicator in main_topic_indicators):
        # Avoid treating detailed sub-actions as main topics
        sub_action_indicators = [
            'remove', 'strip', 'fix', 'map', 'merge', 'drop', 'find', 
            'parse', 'convert data types', 'impute', 'encode categorical'
        ]
        if not any(sub_indicator in line_lower for sub_indicator in sub_action_indicators):
            return True
    
    return False

def generate_agent_name(topic):
    """Generate descriptive agent name from topic"""
    topic_lower = topic.lower()
    
    # Define agent name mappings
    agent_mappings = {
        'load': 'Raw Data Handler Agent',
        'inspect': 'Data Inspector Agent', 
        'clean': 'Data Cleaner Agent',
        'column': 'Column Manager Agent',
        'data type': 'Data Type Manager Agent',
        'inconsistent': 'Inconsistency Resolver Agent',
        'outlier': 'Outlier Handler Agent',
        'missing': 'Missing Data Handler Agent',
        'duplicate': 'Duplicate Data Handler Agent',
        'standardize': 'Value Standardizer Agent',
        'encode': 'Categorical Encoder Agent',
        'validate': 'Data Validator Agent',
        'normalize': 'Data Normalizer Agent'
    }
    
    for keyword, agent_name in agent_mappings.items():
        if keyword in topic_lower:
            return agent_name
    
    # Default agent name
    return f"{topic.split('.')[0].strip().title()} Handler Agent"

def generate_agent_description(topic):
    """Generate descriptive agent description from topic"""
    topic_lower = topic.lower()
    
    # Define agent description mappings
    agent_descriptions = {
        'load': 'Manages the initial acquisition and loading of raw data from various sources including databases, files, and APIs.',
        'inspect': 'Performs comprehensive inspection and profiling of data to understand structure, quality, and characteristics.',
        'clean': 'Handles data cleaning operations including removing inconsistencies, duplicates, and handling missing values.',
        'column': 'Manages column-level operations including renaming, reordering, and metadata management.',
        'data type': 'Handles data type conversions and ensures proper data type assignments across the dataset.',
        'inconsistent': 'Identifies and resolves data inconsistencies, standardizes formats, and ensures data integrity.',
        'outlier': 'Detects, analyzes, and handles outliers using statistical methods and domain knowledge.',
        'missing': 'Implements strategies for handling missing data including imputation, removal, and flagging.',
        'duplicate': 'Identifies and removes duplicate records while preserving data integrity and relationships.',
        'standardize': 'Standardizes data values, formats, and structures to ensure consistency across the dataset.',
        'encode': 'Handles categorical data encoding including one-hot encoding, label encoding, and feature engineering.',
        'validate': 'Performs data validation checks to ensure data quality, completeness, and business rule compliance.',
        'normalize': 'Applies normalization and scaling techniques to prepare data for analysis and modeling.'
    }
    
    for keyword, description in agent_descriptions.items():
        if keyword in topic_lower:
            return description
    
    # Default description
    return f"Handles {topic.lower()} operations and ensures proper processing of related tasks."

def generate_subagent_name(topic):
    """Generate descriptive subagent name from topic"""
    topic_lower = topic.lower()
    
    # Define subagent name mappings
    subagent_mappings = {
        'load': 'Data Loader',
        'inspect': 'Data Inspector',
        'clean': 'Data Cleaner',
        'column': 'Column Processor',
        'data type': 'Type Converter',
        'inconsistent': 'Consistency Manager',
        'outlier': 'Outlier Detector',
        'missing': 'Missing Value Handler',
        'duplicate': 'Duplicate Resolver',
        'standardize': 'Value Standardizer',
        'encode': 'Category Encoder',
        'validate': 'Data Validator',
        'normalize': 'Data Normalizer'
    }
    
    for keyword, subagent_name in subagent_mappings.items():
        if keyword in topic_lower:
            return subagent_name
    
    # Default subagent name
    return f"{topic.split('.')[0].strip().title()} Processor"

def generate_subagent_description(topic):
    """Generate descriptive subagent description from topic"""
    topic_lower = topic.lower()
    
    # Define subagent description mappings
    subagent_descriptions = {
        'load': 'Executes data loading operations from various sources and handles connection management.',
        'inspect': 'Performs detailed data inspection and generates comprehensive data quality reports.',
        'clean': 'Implements specific data cleaning algorithms and quality improvement procedures.',
        'column': 'Handles column-specific transformations and metadata operations.',
        'data type': 'Executes data type conversions and validates type consistency.',
        'inconsistent': 'Identifies inconsistencies and applies standardization rules.',
        'outlier': 'Detects anomalies and applies appropriate outlier treatment strategies.',
        'missing': 'Implements missing data strategies including imputation and removal techniques.',
        'duplicate': 'Identifies duplicate records and applies deduplication algorithms.',
        'standardize': 'Applies standardization rules and format conversions.',
        'encode': 'Performs categorical encoding and feature transformation operations.',
        'validate': 'Executes validation rules and ensures data quality standards.',
        'normalize': 'Applies normalization algorithms and scaling transformations.'
    }
    
    for keyword, description in subagent_descriptions.items():
        if keyword in topic_lower:
            return description
    
    # Default description
    return f"Processes {topic.lower()} related tasks and maintains data quality standards."

def create_default_structure(lines):
    """Create a comprehensive default structure for data processing"""
    
    # Group actions by categories with descriptions
    categories = {
        'Raw Data Handler Agent': {
            'description': 'Manages the initial acquisition and loading of raw data from various sources including databases, files, and APIs.',
            'subagents': {
                'Data Loader': {
                    'description': 'Executes data loading operations from various sources and handles connection management.',
                    'actions': []
                }
            }
        },
        'Column Manager Agent': {
            'description': 'Manages column-level operations including renaming, reordering, and metadata management.',
            'subagents': {
                'Column Processor': {
                    'description': 'Handles column-specific transformations and metadata operations.',
                    'actions': []
                }
            }
        },
        'Data Type Manager Agent': {
            'description': 'Handles data type conversions and ensures proper data type assignments across the dataset.',
            'subagents': {
                'Type Converter': {
                    'description': 'Executes data type conversions and validates type consistency.',
                    'actions': []
                }
            }
        },
        'Data Cleaner Agent': {
            'description': 'Handles data cleaning operations including removing inconsistencies, duplicates, and handling missing values.',
            'subagents': {
                'Data Processor': {
                    'description': 'Implements specific data cleaning algorithms and quality improvement procedures.',
                    'actions': []
                }
            }
        }
    }
    
    # Categorize actions based on keywords
    for line in lines:
        line_clean = line[2:] if line.startswith('- ') else line
        line_lower = line_clean.lower()
        
        if any(keyword in line_lower for keyword in ['load', 'import', 'extract', 'file format', 'encoding']):
            categories['Raw Data Handler Agent']['subagents']['Data Loader']['actions'].append(line_clean)
        elif any(keyword in line_lower for keyword in ['column', 'header', 'metadata', 'whitespace']):
            categories['Column Manager Agent']['subagents']['Column Processor']['actions'].append(line_clean)
        elif any(keyword in line_lower for keyword in ['data type', 'convert', 'numeric', 'categorical', 'parse']):
            categories['Data Type Manager Agent']['subagents']['Type Converter']['actions'].append(line_clean)
        else:
            categories['Data Cleaner Agent']['subagents']['Data Processor']['actions'].append(line_clean)
    
    # Build agents structure
    agents = []
    for agent_name, agent_data in categories.items():
        subagents = []
        for subagent_name, subagent_data in agent_data['subagents'].items():
            if subagent_data['actions']:  # Only include subagents with actions
                subagents.append({
                    "name": subagent_name,
                    "description": subagent_data['description'],
                    "actions": subagent_data['actions']
                })
        
        if subagents:  # Only include agents with subagents
            agents.append({
                "name": agent_name,
                "description": agent_data['description'],
                "subagents": subagents
            })
    
    return agents

def parse_json_response(raw_response):
    """Parse and clean JSON response"""
    try:
        # Clean up possible ```json wrappers
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw_response.strip(), flags=re.MULTILINE).strip()
        
        # Parse JSON
        parsed = json.loads(cleaned)
        return parsed, None
        
    except json.JSONDecodeError as e:
        return None, f"JSON parsing error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

@app.route('/')
def index():
    """Serve the main interface"""
    with open('index.html', 'r') as f:
        return f.read()

@app.route('/process', methods=['POST'])
def process_document():
    """Process uploaded PDF document"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Extract text from PDF
            print(f"[INFO] Processing file: {file.filename}")
            mindmap_text = extract_text_from_pdf(temp_path)
            
            if not mindmap_text:
                return jsonify({'error': 'No text could be extracted from the PDF'}), 400
            
            print(f"[DEBUG] Extracted text:\n{mindmap_text}")
            
            # Send to Mistral agent
            print("[INFO] Sending to Mistral agent...")
            raw_output = ask_mistral_agent(mindmap_text)
            
            # Parse JSON response
            parsed_json, parse_error = parse_json_response(raw_output)
            
            if parse_error:
                return jsonify({'error': parse_error}), 500
            
            # Save output files
            os.makedirs('outputs', exist_ok=True)
            base_filename = secure_filename(os.path.splitext(file.filename)[0])
            
            # Save raw response
            raw_path = f"outputs/{base_filename}_raw_response.txt"
            with open(raw_path, "w", encoding="utf-8") as raw_file:
                raw_file.write(raw_output)
            
            # Save parsed JSON
            json_path = f"outputs/{base_filename}_output.json"
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(parsed_json, json_file, indent=2)
            
            # Save extracted text for debugging
            debug_path = f"outputs/{base_filename}_extracted_text.txt"
            with open(debug_path, "w", encoding="utf-8") as debug_file:
                debug_file.write(mindmap_text)
            
            print(f"[SUCCESS] Files saved: {json_path}, {raw_path}, {debug_path}")
            
            return jsonify({
                'success': True,
                'json_data': parsed_json,
                'raw_response': raw_output,
                'extracted_text': mindmap_text,
                'files_saved': {
                    'json': json_path,
                    'raw': raw_path,
                    'debug': debug_path
                }
            })
            
        finally:
            # Clean up temporary file
            os.unlink(temp_path)
            
    except Exception as e:
        print(f"[ERROR] Processing failed: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Agent Script Interface'})

if __name__ == '__main__':
    # Create outputs directory if it doesn't exist
    os.makedirs('outputs', exist_ok=True)
    
    print("Starting Agent Script Interface Module...")
    print("Make sure Mistral is running on localhost:11434")
    print("Access the interface at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)