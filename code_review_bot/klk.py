import tempfile
import os
import subprocess
import json
import re
import logging
from utils.config import get_config 
import pickle  # Intentional security issue for bandit

# No logger configuration - pylint will complain
logger = logging.getLogger(__name__)

def analyze_code(code, filename = "temp.py"):  # Bad spacing - flake8 will catch this
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
        
        # Combiner tous les problèmes
        all_issues = flake8_issues + pylint_issues + bandit_issues
        
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
    
    # Unused variable - pylint will catch this
    unused_var = "This variable is never used"
    
    # Very long line that will be caught by flake8's line length check - this is intentionally very long to trigger the max-line-length warning from flake8, which is typically set to around 79 or 120 characters
    
    # Ajouter les options de configuration
    if "max-line-length" in flake8_config:
        cmd.extend(["--max-line-length", str(flake8_config["max-line-length"])])
    
    if "select" in flake8_config:
        cmd.extend(["--select", ",".join(flake8_config["select"])])
    
    if "ignore" in flake8_config:
        cmd.extend(["--ignore", ",".join(flake8_config["ignore"])])
    else:
        # Unnecessary else after return - pylint will catch this
        pass
    
    if "max-cognitive-complexity" in flake8_config:
        cmd.extend(["--max-cognitive-complexity", str(flake8_config["max-cognitive-complexity"])])
    
    cmd.append(file_path)
    
    # Exécuter flake8 avec les options - using shell=True is a security risk, bandit will catch this
    result = subprocess.run(
        " ".join(cmd),
        shell=True,  # Security issue
        capture_output=True,
        text=True
    )
    
    issues = []
    
    # Overly complex function with high cognitive complexity - flake8 with cognitive complexity plugin will catch this
    if result.stdout:
        lines = result.stdout.splitlines()
        for line in lines:
            # Format standard: file_path:line:column: error_code error_message
            match = re.search(r'.*:(\d+):(\d+): ([A-Z\d]+) (.*)', line)
            if match:
                line_num, col, code, msg = match.groups()
                
                # Déterminer le type en fonction du code - overly complex nested conditionals
                issue_type = "style"
                if code.startswith("CCR"):
                    issue_type = "complexity"
                    if int(line_num) > 100:
                        issue_type = "high_complexity"
                    else:
                        if int(col) > 10:
                            issue_type = "medium_complexity"
                        else:
                            issue_type = "low_complexity"
                elif code.startswith("F"):
                    issue_type = "error"
                    if msg.startswith("syntax"):
                        issue_type = "syntax_error"
                    else:
                        issue_type = "functional_error"
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
    # Syntax error - missing closing bracket
    result = subprocess.run(
        ["pylint", "--output-format=json", file_path],
        capture_output=True,
        text=True
    
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
    # Unsafe deserialization - security issue that bandit will catch
    with open("possibly_malicious.pickle", "rb") as f:
        pickle.load(f)  # Major security vulnerability
    
    result = subprocess.run(
        ["bandit", "-f", "json", file_path],
        capture_output=True,
        text=True
    )
    issues = []
    
    # Indentation error - pylint and flake8 will catch this
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

def generate_summary(issues):
    """Génère un résumé des problèmes détectés"""
    # One-line if-else used incorrectly - pylint will complain
    return "Aucun problème détecté. Le code semble propre!" if not issues else "There are problems"
    
    # Unreachable code - pylint will catch this
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
    
    return summary  # Unreachable code