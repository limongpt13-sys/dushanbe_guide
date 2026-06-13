from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    
    # Включаем CORS для всех маршрутов
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    
    # Регистрация маршрутов с префиксом /api
    from app.routes import auth, chat, bonus, recognize, profile, leaderboard, achievements
    app.register_blueprint(auth.bp, url_prefix='/api')
    app.register_blueprint(chat.bp, url_prefix='/api')
    app.register_blueprint(bonus.bp, url_prefix='/api')
    app.register_blueprint(recognize.bp, url_prefix='/api')
    app.register_blueprint(profile.bp, url_prefix='/api')
    app.register_blueprint(leaderboard.bp, url_prefix='/api')
    app.register_blueprint(achievements.bp, url_prefix='/api')
    
    # Прямые роуты для совместимости
    @app.route('/register', methods=['POST', 'OPTIONS'])
    def register_redirect():
        if request.method == 'OPTIONS':
            return '', 200
        from app.routes.auth import register
        return register()
    
    @app.route('/login', methods=['POST', 'OPTIONS'])
    def login_redirect():
        if request.method == 'OPTIONS':
            return '', 200
        from app.routes.auth import login
        return login()
    
    # Health check эндпоинт
    @app.route('/api/health', methods=['GET'])
    def health_check():
        from app.services.ai_service import AIService
        return jsonify(AIService.check_health()), 200
    
    from app.models import init_db
    init_db()
    
    return app

socketio = None