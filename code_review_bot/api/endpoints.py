from flask_restx import Api, Resource, Namespace, fields
from flask import request
from analyzers.linters import analyze_code

# Initialisation de l'API
api = Api(
    title="Code Review Bot API",
    version="1.0",
    description="API pour l'analyse automatique de code Python",
)

# Création d'un namespace pour les endpoints d'analyse
ns = api.namespace('analyze', description='Endpoints pour l\'analyse de code')

# Modèles pour la documentation de l'API
code_input = api.model('CodeInput', {
    'code': fields.String(required=True, description='Code Python à analyser'),
    'filename': fields.String(required=False, description='Nom du fichier (optionnel)', default='temp.py')
})

issue_model = api.model('Issue', {
    'line': fields.Integer(description='Numéro de ligne'),
    'column': fields.Integer(description='Numéro de colonne'),
    'type': fields.String(description='Type de problème'),
    'message': fields.String(description='Description du problème'),
    'source': fields.String(description='Outil qui a détecté le problème')
})

analysis_result = api.model('AnalysisResult', {
    'issues': fields.List(fields.Nested(issue_model), description='Liste des problèmes détectés'),
    'summary': fields.String(description='Résumé de l\'analyse')
})

@ns.route('/code')
class CodeAnalysis(Resource):
    @ns.expect(code_input)
    @ns.marshal_with(analysis_result)
    def post(self):
        """Analyser un snippet de code Python"""
        data = request.json
        code = data.get('code')
        filename = data.get('filename', 'temp.py')
        
        # Analyser le code avec nos outils
        result = analyze_code(code, filename)
        
        return result