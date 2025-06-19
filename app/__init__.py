from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_mail import Mail
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
import os
from datetime import datetime

db = SQLAlchemy()
mail = Mail()
socketio = SocketIO(cors_allowed_origins="*")
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    basedir = os.path.abspath(os.path.dirname(__file__))
    static_dir = os.path.join(basedir, 'static')
    app = Flask(__name__, static_folder=static_dir)

    app.config['SECRET_KEY'] = 'secret-lele'
    db_path = os.path.join(basedir, '..', 'database', 'lele.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'uploads')

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'agunghandiko2000@gmail.com'
    app.config['MAIL_PASSWORD'] = 'gbpz jegn xbwv uzeq'
    app.config['MAIL_DEFAULT_SENDER'] = 'agunghandiko2000@gmail.com'

    # Inisialisasi extension
    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    login_manager.init_app(app)
    app.login_manager = login_manager
    login_manager.login_view = 'main.login'

    # User loader
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprint utama
    from .routes import main
    app.register_blueprint(main, url_prefix="/")

    # Blueprint admin
    from .blueprints.admin_routes import admin
    app.register_blueprint(admin, url_prefix="/admin")

    # Inject notifikasi
    @app.context_processor
    def inject_unseen_notifications():
        from .models import Notification
        if current_user.is_authenticated:
            count = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).count()
            return {'unseen_notifications': count}
        return {'unseen_notifications': 0}

    # Filter waktu (time ago)
    def time_ago(dt):
        now = datetime.utcnow()
        diff = now - dt
        seconds = diff.total_seconds()
        minutes = seconds / 60
        hours = minutes / 60
        days = hours / 24

        if seconds < 60:
            return "Baru saja"
        elif minutes < 60:
            return f"{int(minutes)} menit yang lalu"
        elif hours < 24:
            return f"{int(hours)} jam yang lalu"
        elif days < 7:
            return f"{int(days)} hari yang lalu"
        else:
            return dt.strftime("%d %B %Y")

    app.jinja_env.filters['time_ago'] = time_ago

    return app
