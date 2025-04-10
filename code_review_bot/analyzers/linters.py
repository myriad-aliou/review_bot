import tempfile
import os
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
        pip_audit_issues = run_pip_audit()  # New function for pip-audit
        
        # Combiner tous les problèmes
        all_issues = flake8_issues + pylint_issues + bandit_issues + pip_audit_issues
        
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
    # Existing run_flake8 function remains the same
    pass

def run_pylint(file_path):
    # Existing run_pylint function remains the same
    pass

def run_bandit(file_path):
    # Existing run_bandit function remains the same
    pass

def run_pip_audit():
    """Exécute pip-audit pour détecter les vulnérabilités des dépendances"""
    result = subprocess.run(
        ["pip-audit", "--format", "json"],
        capture_output=True,
        text=True
    )
    issues = []
    
    if result.stdout:
        try:
            pip_audit_output = json.loads(result.stdout)
            for advisory in pip_audit_output:
                issues.append({
                    "line": 0,  # pip-audit doesn't provide line numbers
                    "column": 0,  # pip-audit doesn't provide column information
                    "type": "security",
                    "message": f"Vulnerability found: {advisory['advisory']['summary']} (Package: {advisory['package']}, Version: {advisory['version']})",
                    "source": "pip-audit"
                })
        except json.JSONDecodeError:
            # Fallback si la sortie JSON n'est pas valide
            pass
    
    return issues

def generate_summary(issues):
    # Existing generate_summary function remains the same
    pass
