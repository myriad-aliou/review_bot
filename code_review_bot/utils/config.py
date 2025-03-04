"""
Configuration globale pour le bot de code review
"""

# Configuration par défaut pour les linters
DEFAULT_LINTER_CONFIG = {
    "flake8": {
        "max-line-length": 100,
        "ignore": ["E203", "W503"],  # Compatibilité avec Black
        "select": ["E", "F", "W", "C90", "SIM", "CCR"],  # Inclure les codes CCR pour cognitive complexity
        "max-cognitive-complexity": 10  # Seuil au-delà duquel une alerte est générée 
    },
    "pylint": {
        "disable": [
            "missing-docstring",
            "invalid-name"
        ]
    },
    "bandit": {
        "exclude": ["tests"]
    }
}

# Niveaux de sévérité
SEVERITY_LEVELS = {
    "error": 3,
    "warning": 2,
    "convention": 1,
    "refactor": 1,
    "info": 0
}

def get_config():
    """
    Récupère la configuration des linters.
    Plus tard, cela pourrait charger à partir d'un fichier de configuration.
    """
    return DEFAULT_LINTER_CONFIG