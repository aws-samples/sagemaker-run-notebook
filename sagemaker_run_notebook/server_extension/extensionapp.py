from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler


class HelloWorldHandler(IPythonHandler):
    def get(self):
        self.finish("Hello, world!")


def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.

    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """
    web_app = nb_server_app.web_app
    host_pattern = ".*$"
    route_pattern = url_path_join(web_app.settings["base_url"], "/hello")
    web_app.add_handlers(host_pattern, [(route_pattern, HelloWorldHandler)])
