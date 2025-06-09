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
    
    # Prompt amélioré pour obtenir une réponse structurée
    prompt = f"""Analyze this Python code for quality, security, and optimization issues.
File: {filename}

Code with line numbers:
{numbered_code}

Please respond ONLY with a JSON array of issues in this exact format(like this):
{
  "issues": [
    {
      "line": 1,
      "column": 1,
      "type": "error",
      "message": "F821: undefined name 'string'",
      "source": "flake8"
    },
    {
      "line": 1,
      "column": 7,
      "type": "warning",
      "message": "W292: no newline at end of file",
      "source": "flake8"
    },
    {
      "line": 1,
      "column": 0,
      "type": "convention",
      "message": "Final newline missing",
      "source": "pylint"
    }
    ]
}

Focus on:
- Security vulnerabilities
- Performance bottlenecks  
- Code smells and anti-patterns
- Best practices violations
- Potential bugs

Return empty array [] if no issues found. Do not include explanatory text, only the JSON array."""

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
                        "temperature": 0.1,  # Plus déterministe
                        "top_p": 0.9
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            content = data.get("response", "").strip()
            
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
        # Nettoyer la réponse (enlever markdown, texte superflu)
        cleaned_content = content.strip()
        
        # Chercher un bloc JSON dans la réponse
        json_match = re.search(r'\[.*\]', cleaned_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            # Fallback: essayer de parser toute la réponse
            json_str = cleaned_content
        
        # Parser le JSON
        raw_issues = json.loads(json_str)
        
        if not isinstance(raw_issues, list):
            return None
        
        # Convertir au format attendu
        parsed_issues = []
        for issue in raw_issues:
            if not isinstance(issue, dict):
                continue
                
            # Validation des champs requis
            if "line" not in issue or "message" not in issue:
                continue
                
            parsed_issue = {
                "line": int(issue.get("line", 1)),
                "column": 0,
                "type": issue.get("type", "info"),
                "message": issue.get("message", "Unknown issue"),
                "source": "ollama"
            }
            
            # Ajouter la sévérité si disponible
            if "severity" in issue:
                parsed_issue["message"] = f"[{issue['severity'].upper()}] {parsed_issue['message']}"
            
            parsed_issues.append(parsed_issue)
        
        return parsed_issues
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.debug(f"Content that failed to parse: {content[:200]}...")
        return None
    except Exception as e:
        logger.error(f"Error parsing Ollama response: {e}")
        return None



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