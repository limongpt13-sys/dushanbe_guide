from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    
    # Регистрация маршрутов
    from app.routes import auth, chat, bonus, recognize, profile, leaderboard, achievements
    app.register_blueprint(auth.bp, url_prefix='/api')
    app.register_blueprint(chat.bp, url_prefix='/api')
    app.register_blueprint(bonus.bp, url_prefix='/api')
    app.register_blueprint(recognize.bp, url_prefix='/api')
    app.register_blueprint(profile.bp, url_prefix='/api')
    app.register_blueprint(leaderboard.bp, url_prefix='/api')
    app.register_blueprint(achievements.bp, url_prefix='/api')
    
    # Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        from app.services.ai_service import AIService
        return jsonify(AIService.check_health()), 200
    
    from app.models import init_db
    init_db()
    
    return app