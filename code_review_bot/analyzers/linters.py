import tempfile
import os
import requests
import subprocess
import json
import re
import logging
from utils.config import get_config 

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_code(code, filename="temp.py"):
    """
    Analyse le code Python fourni avec différents linters
    
    Args:
        code (str): Le code Python à analyser
        filename (str): Nom du fichier pour le code (utile pour certains linters)
        
    Returns:
        dict: Résultats de l'analyse avec les problèmes détectés
    """
    # Créer un fichier temporaire avec le code
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp:
        temp.write(code.encode('utf-8'))
        temp_path = temp.name
    
    try:
        # Collecter les résultats de différents linters
        flake8_issues = run_flake8(temp_path)
        pylint_issues = run_pylint(temp_path)
        bandit_issues = run_bandit(temp_path)
        #pip_audit_issues = run_pip_audit()
        ollama_issues = run_ollama(temp_path, filename)
        
        # Combiner tous les problèmes
        all_issues = flake8_issues + pylint_issues + bandit_issues + ollama_issues #+ pip_audit_issues
        
        # Générer un résumé
        summary = generate_summary(all_issues)
        
        return {
            "issues": all_issues,
            "summary": summary
        }
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def run_flake8(file_path):
    """Exécute Flake8 sur le fichier et parse les résultats avec cognitive complexity"""
    # Récupérer la configuration
    config = get_config()
    flake8_config = config.get("flake8", {})
    
    # Préparer les arguments avec la configuration
    cmd = ["flake8"]
    
    # Ajouter les options de configuration
    if "max-line-length" in flake8_config:
        cmd.extend(["--max-line-length", str(flake8_config["max-line-length"])])
    
    if "select" in flake8_config:
        cmd.extend(["--select", ",".join(flake8_config["select"])])
    
    if "ignore" in flake8_config:
        cmd.extend(["--ignore", ",".join(flake8_config["ignore"])])
    
    if "max-cognitive-complexity" in flake8_config:
        cmd.extend(["--max-cognitive-complexity", str(flake8_config["max-cognitive-complexity"])])
    
    cmd.append(file_path)
    
    # Exécuter flake8 avec les options
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    
    issues = []
    
    if result.stdout:
        lines = result.stdout.splitlines()
        for line in lines:
            # Format standard: file_path:line:column: error_code error_message
            match = re.search(r'.*:(\d+):(\d+): ([A-Z\d]+) (.*)', line)
            if match:
                line_num, col, code, msg = match.groups()
                
                # Déterminer le type en fonction du code
                issue_type = "style"
                if code.startswith("CCR"):
                    issue_type = "complexity"
                elif code.startswith("F"):
                    issue_type = "error"
                elif code.startswith("E"):
                    issue_type = "error"
                elif code.startswith("W"):
                    issue_type = "warning"
                
                issues.append({
                    "line": int(line_num),
                    "column": int(col),
                    "type": issue_type,
                    "message": f"{code}: {msg}",
                    "source": "flake8"
                })
    
    return issues

def run_pylint(file_path):
    """Exécute Pylint sur le fichier et parse les résultats"""
    result = subprocess.run(
        ["pylint", "--output-format=json", file_path],
        capture_output=True,
        text=True
    )
    issues = []
    
    if result.stdout:
        try:
            pylint_output = json.loads(result.stdout)
            for error in pylint_output:
                issues.append({
                    "line": error["line"],
                    "column": error["column"],
                    "type": error["type"],
                    "message": error["message"],
                    "source": "pylint"
                })
        except json.JSONDecodeError:
            # Fallback si la sortie JSON n'est pas valide
            pass
    
    return issues

def run_bandit(file_path):
    """Exécute Bandit sur le fichier et parse les résultats"""
    result = subprocess.run(
        ["bandit", "-f", "json", file_path],
        capture_output=True,
        text=True
    )
    issues = []
    
    if result.stdout:
        try:
            bandit_output = json.loads(result.stdout)
            results = bandit_output.get("results", [])
            for error in results:
                issues.append({
                    "line": error["line_number"],
                    "column": 0,  # Bandit ne fournit pas toujours la colonne
                    "type": "security",
                    "message": error["issue_text"],
                    "source": "bandit"
                })
        except json.JSONDecodeError:
            # Fallback si la sortie JSON n'est pas valide
            pass
    
    return issues

##ajout ollama


def run_ollama(code, filename):
    """Exécute l'analyse de code via Ollama avec parsing structuré"""
    config = get_config()
    ollama_config = config.get("ollama", {})
    
    # Configuration par défaut
    ollama_model = ollama_config.get("model", "deepseek-coder:latest")
    ollama_host = ollama_config.get("host", "http://rnoqi-154-124-39-72.a.free.pinggy.link")
    timeout = ollama_config.get("timeout", 30)
    max_retries = ollama_config.get("max_retries", 2)
    
    # Vérifier si Ollama est activé
    if not ollama_config.get("enabled", True):
        logger.info("Ollama analysis disabled in configuration")
        return []
    
    # Numéroter les lignes pour le contexte
    numbered_lines = []
    for i, line in enumerate(code.split('\n'), 1):
        numbered_lines.append(f"{i:3d}: {line}")
    numbered_code = '\n'.join(numbered_lines)
    
    # Prompt simplifié et plus direct
    prompt = f"""Analyze this Python code and return ONLY a valid JSON response.

File: {filename}
Code:
{numbered_code}

Return a JSON object with this exact structure:
{{
  "issues": [
    {{
      "line": 1,
      "column": 0,
      "type": "warning",
      "message": "Issue description",
      "source": "ollama"
    }}
  ]
}}

If no issues found, return: {{"issues": []}}

IMPORTANT: 
- Return ONLY valid JSON, no other text
- Each issue must have: line (number), column (number), type (string), message (string), source (string)
- Types can be: error, warning, info, convention
- Focus on: security, performance, code quality, best practices"""

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Ollama analysis attempt {attempt + 1}/{max_retries + 1}")
            
            response = requests.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 2000,  # Limit response length
                        "stop": ["\n\n", "```"]  # Stop at common text indicators
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            content = data.get("response", "").strip()
            
            # Log the raw response for debugging
            logger.debug(f"Raw Ollama response: {content[:200]}...")
            
            if not content:
                logger.warning("Empty response from Ollama")
                continue
                
            # Parser la réponse JSON
            issues = parse_ollama_response(content)
            
            if issues is not None:
                logger.info(f"Ollama found {len(issues)} issues")
                return issues
            else:
                logger.warning(f"Failed to parse Ollama response on attempt {attempt + 1}")
                logger.debug(f"Response content: {content}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timeout on attempt {attempt + 1}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama on attempt {attempt + 1}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request error on attempt {attempt + 1}: {e}")
        except Exception as e:
            logger.error(f"Unexpected Ollama error on attempt {attempt + 1}: {e}")
    
    # Si tous les essais échouent, retourner un message d'information
    logger.error("All Ollama analysis attempts failed")
    return [{
        "line": 1,
        "column": 0,
        "type": "info",
        "message": "Ollama AI analysis unavailable (service error)",
        "source": "ollama"
    }]


def parse_ollama_response(content):
    """Parse la réponse d'Ollama pour extraire les issues structurées"""
    try:
        # Log the content we're trying to parse
        logger.debug(f"Parsing content: {content}")
        
        # Nettoyer la réponse
        cleaned_content = content.strip()
        
        # Remove common prefixes/suffixes that might interfere
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        if cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        
        cleaned_content = cleaned_content.strip()
        
        # If empty after cleaning, return empty list
        if not cleaned_content:
            logger.warning("Content is empty after cleaning")
            return []
        
        # Try to find JSON in the response
        json_patterns = [
            r'\{[^{}]*"issues"[^{}]*\[[^\]]*\][^{}]*\}',  # Look for issues array
            r'\{.*\}',  # Any JSON object
            r'\[.*\]'   # Any JSON array
        ]
        
        json_str = None
        for pattern in json_patterns:
            match = re.search(pattern, cleaned_content, re.DOTALL)
            if match:
                json_str = match.group(0)
                break
        
        if not json_str:
            # If no JSON pattern found, try the whole content
            json_str = cleaned_content
        
        logger.debug(f"Attempting to parse JSON: {json_str}")
        
        # Parse JSON
        try:
            parsed_data = json.loads(json_str)
        except json.JSONDecodeError:
            # Try to fix common JSON issues
            json_str = json_str.replace("'", '"')  # Replace single quotes
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # Remove trailing commas
            parsed_data = json.loads(json_str)
        
        # Handle different response formats
        if isinstance(parsed_data, dict):
            if "issues" in parsed_data:
                raw_issues = parsed_data["issues"]
            else:
                # If it's a dict but no issues key, treat as single issue
                raw_issues = [parsed_data]
        elif isinstance(parsed_data, list):
            raw_issues = parsed_data
        else:
            logger.error(f"Unexpected JSON structure: {type(parsed_data)}")
            return None
        
        # Validate and convert issues
        parsed_issues = []
        for issue in raw_issues:
            if not isinstance(issue, dict):
                continue
            
            # Validation des champs requis
            if "line" not in issue or "message" not in issue:
                logger.warning(f"Issue missing required fields: {issue}")
                continue
            
            try:
                parsed_issue = {
                    "line": int(issue.get("line", 1)),
                    "column": int(issue.get("column", 0)),
                    "type": issue.get("type", "info"),
                    "message": str(issue.get("message", "Unknown issue")),
                    "source": "ollama"
                }
                
                # Validate line number
                if parsed_issue["line"] < 1:
                    parsed_issue["line"] = 1
                
                # Validate type
                if parsed_issue["type"] not in ["error", "warning", "info", "convention"]:
                    parsed_issue["type"] = "info"
                
                parsed_issues.append(parsed_issue)
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing issue {issue}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(parsed_issues)} issues")
        return parsed_issues
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Content that failed to parse: {content}")
        return None
    except Exception as e:
        logger.error(f"Error parsing Ollama response: {e}")
        logger.error(f"Content: {content}")
        return None


def test_ollama_connection():
    """Test function to check Ollama connectivity"""
    config = get_config()
    ollama_config = config.get("ollama", {})
    ollama_host = ollama_config.get("host", "http://rnoqi-154-124-39-72.a.free.pinggy.link")
    
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=10)
        if response.status_code == 200:
            logger.info("Ollama connection successful")
            return True
        else:
            logger.error(f"Ollama connection failed with status: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Ollama connection test failed: {e}")
        return False

def test_ollama_connection():
    """Test function to check Ollama connectivity"""
    config = get_config()
    ollama_config = config.get("ollama", {})
    ollama_host = ollama_config.get("host", "http://rnoqi-154-124-39-72.a.free.pinggy.link")
    
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=10)
        if response.status_code == 200:
            logger.info("Ollama connection successful")
            return True
        else:
            logger.error(f"Ollama connection failed with status: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Ollama connection test failed: {e}")
        return False



def generate_summary(issues):
    """Génère un résumé des problèmes détectés"""
    if not issues:
        return "Aucun problème détecté. Le code semble propre!"
    
    # Compter les problèmes par type et par source
    sources = {}
    types = {}
    
    for issue in issues:
        source = issue["source"]
        issue_type = issue["type"]
        
        sources[source] = sources.get(source, 0) + 1
        types[issue_type] = types.get(issue_type, 0) + 1
    
    summary = f"Détecté {len(issues)} problème(s):\n"
    
    for source, count in sources.items():
        summary += f"- {count} par {source}\n"
    
    for issue_type, count in types.items():
        summary += f"- {count} de type {issue_type}\n"
    
    return summary