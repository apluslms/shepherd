from apluslms_shepherd import create_app
from apluslms_shepherd.extensions import celery

app = create_app()
celery.init_app(app)

if __name__ == '__main__':
    with app.app_context():
        celery.start()
