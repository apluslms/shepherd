from apluslms_shepherd import create_app
from flask_script import Manager
from flask_migrate import MigrateCommand

app = create_app()
with app.app_context():
    manager = Manager(app)
    manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()