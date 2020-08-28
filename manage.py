from flask_script import Manager,Server,Shell
from flask_migrate import Migrate
from flask_migrate import MigrateCommand


from flask_k8s import create_app
# from flask_k8s import models

app = create_app()
manager = Manager(app)

# migrate = Migrate(app,models.db)

#python manager.py server  取代runserver
#黑科技段
# def make_shell_context():
#     return dict(app=app, db=models.db, Cluster=models.Cluster)

# manager.add_command("shell", Shell(make_context=make_shell_context))

#
manager.add_command("server", Server(host='0.0.0.0', port=8082))
# manager.add_command("db", MigrateCommand)

if __name__ == "__main__":
    manager.run()