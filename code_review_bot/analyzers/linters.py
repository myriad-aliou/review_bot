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
        ollama_issues = run_ollama(code)
        
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


def run_ollama(code):
    """Exécute l'analyse de code via Ollama (modèle Deepseek)"""
    config = get_config()
    ollama_model = config.get("ollama", {}).get("model", "deepseek-coder:latest")
    ollama_host = config.get("ollama", {}).get("host", "http://rnkpp-154-124-39-72.a.free.pinggy.link")

    try:
        prompt = f"Analyse ce code Python et retourne les problèmes de qualité, sécurité ou optimisation :\n\n{code}"
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={"model": ollama_model, "prompt": prompt, "stream": False}
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("response", "")

        return parse_ollama_response(content)
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return [{
            "line": 1,
            "column": 0,
            "type": "ai",
            "message": "Erreur lors de l'appel à Ollama.",
            "source": "ollama"
        }]


def parse_ollama_response(content):
    """Parse la réponse d'Ollama pour extraire les problèmes individuels avec numéros de ligne"""
    issues = []
    
    # Nettoyer le contenu
    content = content.strip()
    
    # Diviser en lignes et traiter chaque ligne
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Ignorer les lignes vides, les markdown et les commentaires
        if not line or line.startswith('```') or line.startswith('#'):
            continue
            
        # Chercher les patterns avec numéros de ligne
        line_number = extract_line_number(line)
        issue_type = extract_issue_type(line)
        message = clean_message(line)
        
        # Si on a trouvé un numéro de ligne valide et un message significatif
        if line_number > 0 and len(message) > 10:
            issues.append({
                "line": line_number,
                "column": 0,
                "type": issue_type,
                "message": message,
                "source": "ollama"
            })
        elif len(message) > 20:  # Message significatif sans numéro de ligne
            issues.append({
                "line": 1,  # Ligne 1 par défaut
                "column": 0,
                "type": issue_type,
                "message": message,
                "source": "ollama"
            })
    
    # Si aucun problème parsé, retourner le contenu complet
    if not issues and content:
        issues.append({
            "line": 1,
            "column": 0,
            "type": "quality",
            "message": content,
            "source": "ollama"
        })
    
    return issues


def extract_line_number(text):
    """Extrait le numéro de ligne d'un texte"""
    # Patterns pour trouver les numéros de ligne (adaptés aux réponses réelles d'Ollama)
    patterns = [
        r'\[LIGNE-(\d+)\]',         # "[LIGNE-5]"
        r'LIGNE\s+(\d+)',           # "LIGNE 5"
        r'ligne\s+(\d+)',           # "ligne 5"  
        r'L(\d+)',                  # "L5"
        r'(\d+)\s*[-:]\s*\w+\s*[-:]', # "5: TYPE -" ou "5 - TYPE:"
        r'^\s*(\d+)\s*[.)\-]',      # "5." ou "5)" ou "5-" en début de ligne
        r'(\d+)ème\s+Ligne',        # "3ème Ligne"
        r'(\d+)ère\s+Ligne',        # "1ère Ligne"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            line_num = int(match.group(1))
            # Vérifier que c'est un numéro de ligne raisonnable (pas une année ou autre)
            if 1 <= line_num <= 1000:
                return line_num
    
    return 0


def extract_issue_type(text):
    """Extrait le type de problème d'un texte"""
    text_lower = text.lower()
    
    # Mapping des mots-clés vers les types
    type_keywords = {
        'security': ['securite', 'security', 'sécurité', 'mot de passe', 'password', 'eval', 'injection'],
        'performance': ['performance', 'optimisation', 'lent', 'inefficace', 'unused', 'non utilisé'],
        'style': ['style', 'format', 'pep8', 'convention', 'espacement', 'indentation'],
        'error': ['erreur', 'error', 'exception', 'bug'],
        'warning': ['attention', 'warning', 'avertissement'],
        'quality': ['qualite', 'quality', 'qualité', 'code']
    }
    
    # Chercher les mots-clés explicites dans le texte
    for issue_type, keywords in type_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return issue_type
    
    return 'quality'  # Type par défaut


def clean_message(text):
    """Nettoie le message en supprimant les préfixes et formatage"""
    # Supprimer les préfixes de numérotation d'Ollama
    text = re.sub(r'^\s*\d+ère\s+Ligne\s*\[LIGNE-\d+\]\s*:\s*', '', text, flags=re.IGNORECASE)  # "1ère Ligne [LIGNE-5]: "
    text = re.sub(r'^\s*\d+ème\s+Ligne\s*\[LIGNE-\d+\]\s*:\s*', '', text, flags=re.IGNORECASE)  # "3ème Ligne [LIGNE-7]: "
    text = re.sub(r'^\s*\d+\s*[.)\-]\s*', '', text)  # "5. " ou "5) " ou "5- "
    text = re.sub(r'LIGNE\s+\d+\s*[-:]\s*', '', text, flags=re.IGNORECASE)  # "LIGNE 5: "
    text = re.sub(r'ligne\s+\d+\s*[-:]\s*', '', text, flags=re.IGNORECASE)  # "ligne 5: "
    text = re.sub(r'L\d+\s*[-:]\s*', '', text, flags=re.IGNORECASE)  # "L5: "
    text = re.sub(r'\[LIGNE-\d+\]\s*[-:]\s*', '', text, flags=re.IGNORECASE)  # "[LIGNE-5]: "
    
    # Supprimer les types explicites
    types_to_remove = ['QUALITE', 'SECURITE', 'PERFORMANCE', 'STYLE', 'LOGIQUE', 
                      'QUALITY', 'SECURITY', 'PERFORMANCE', 'STYLE', 'LOGIC']
    for type_name in types_to_remove:
        text = re.sub(rf'\b{type_name}\b\s*[-:]\s*', '', text, flags=re.IGNORECASE)
    
    # Supprimer les markdown
    text = re.sub(r'```\w*', '', text)
    text = re.sub(r'```', '', text)
    
    # Nettoyer les espaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


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