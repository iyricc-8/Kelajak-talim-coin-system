import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_upload(file_obj, subfolder='general'):
    """Save an uploaded file and return the relative path."""
    if not file_obj or file_obj.filename == '':
        return None

    if not current_app.config.get('ENABLE_LOCAL_UPLOADS', False):
        current_app.logger.warning('Local uploads are disabled. Skipping file upload.')
        return None

    if not allowed_file(file_obj.filename):
        return None

    ext = file_obj.filename.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    file_obj.save(file_path)
    return f'uploads/{subfolder}/{filename}'


def role_required(*roles):
    """Decorator to restrict access by role."""
    from functools import wraps
    from flask import abort
    from flask_login import current_user, login_required

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
