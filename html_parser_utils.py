

class HtmlParserUtils:
    """
    html转码工具类,里面有一些工具方法用来处理各种语言中的特殊转义字符
    """
    # Js代码中的转义字符
    JS_ESCAPE_MAP = {r"\u000A": "\n", r"\u000D": "\r", r"\u0009": "\t", r"\u003D": "=",
                     r"\u003B": ";", r"\u003C": "<", r"\u0026": "&", r"\u0027": "'",
                     r"\u002D": "-", r"\u003E": ">", r"\u0022": "\"", r"\u005C": "\\"}
    # HTML代码中的转义字符
    HTML_ESCAPE_MAP = {r"a": ""}

    def unescape_html(self, text):
        for key in self.HTML_ESCAPE_MAP:
            text = text.replace(key, self.HTML_ESCAPE_MAP[key])
        return text

    def unescape_js(self, text):
        for key in self.JS_ESCAPE_MAP:
            text = text.replace(key, self.JS_ESCAPE_MAP[key])
        return text
