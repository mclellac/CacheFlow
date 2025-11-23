class NodeData:
    """Data class representing a node in the graph."""

    def __init__(self, name, headers, **kwargs):
        self.name = name
        self.headers = headers
        self.body_color = kwargs.get('body_color', '')
        self.header_color = kwargs.get('header_color', '')
        self.text_color = kwargs.get('text_color', '')
        self.diff_text_color = kwargs.get('diff_text_color', '')
        self.request_url = kwargs.get('request_url', '')
        self.request_host = kwargs.get('request_host', '')
        self.request_method = kwargs.get('request_method', 'GET')

    def get_property(self, name):
        return getattr(self, name, None)
