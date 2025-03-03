import tempfile
import os
import subprocess
import json
import re

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
    """Exécute Flake8 sur le fichier et parse les résultats"""
    result = subprocess.run(
        ["flake8", "--format=json", file_path],
        capture_output=True,
        text=True
    )
    
    issues = []
    
    if result.stdout:
        try:
            flake8_output = json.loads(result.stdout)
            for file_errors in flake8_output.values():
                for error in file_errors:
                    issues.append({
                        "line": error["line_number"],
                        "column": error["column_number"],
                        "type": "style",
                        "message": error["text"],
                        "source": "flake8"
                    })
        except json.JSONDecodeError:
            # Fallback pour les versions de flake8 qui ne supportent pas le format JSON
            lines = result.stdout.splitlines()
            for line in lines:
                match = re.match(r'.*:(\d+):(\d+): (\w+) (.*)', line)
                if match:
                    line_num, col, code, msg = match.groups()
                    issues.append({
                        "line": int(line_num),
                        "column": int(col),
                        "type": "style",
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