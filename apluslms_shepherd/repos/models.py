from apluslms_shepherd.extensions import db


class CRUD(object):
    def save(self):
        db.session.add(self)
        return db.session.commit()

    def delete(self):
        db.session.delete(self)
        return db.session.commit()


class GitRepository(db.Model, CRUD):
    """Define a Git repository, for SSH key management"""
    origin = db.Column(db.String(255), primary_key=True)
    courses = db.relationship('CourseInstance', backref='git_repository', lazy='dynamic')
    public_key = db.Column(db.Text)
    private_key_path = db.Column(db.String)
