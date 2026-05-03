from asgiref.wsgi import WsgiToAsgi

from wsgi import app as wsgi_app

application = WsgiToAsgi(wsgi_app)
