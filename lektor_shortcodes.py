# -*- coding: utf-8 -*-
import re
from urllib.parse import urlparse
from lektor.pluginsystem import Plugin
from lektor.context import get_ctx
from jinja2 import TemplateNotFound

# see https://github.com/lektor/lektor-markdown-highlighter/blob/master/lektor_markdown_highlighter.py
# for case where we need to register dependencies

SHORTCODE = re.compile(r"{{\s*(.*?)\s*}}")

QUOTES = re.compile(r'["]([^"].*?)["]')


def parse_args(s):
    quoted = {}

    def map_quotes(m):
        i = len(quoted)
        k = f"#######{i}#######"
        quoted[k] = m.group(1)
        return k

    def fix_val(v):
        if v in quoted:
            return quoted[v]
        if v.isdigit():
            return int(v)
        return v

    s = QUOTES.sub(map_quotes, s)
    args = s.split()
    kwargs = dict(a.split("=", 1) for a in args if "=" in a)
    args = [a for a in args if "=" not in a]
    kwargs = {k: fix_val(v) for k, v in kwargs.items()}
    args = [fix_val(v) for v in args]
    return args, kwargs


def render(cmd, args, kwargs):
    try:
        ctx = get_ctx()
        if ctx is None:
            return f"[no build context for {cmd}]"
        if args:
            kwargs["args"] = args
        return ctx.env.render_template(
            [
                f"shortcodes/{cmd}.html",
                # "blocks/default.html",
            ],
            pad=ctx.pad,
            this=None,
            values=kwargs,
        )
    except TemplateNotFound:
        return f'[could not find shortcode "{cmd}.html" template]'


def fix_src(url):

    return url.geturl()


class ShortcodesMixin:
    name = "Markdown Shortcodes"
    description = "Embeds shortcodes in Markdown."

    def image(self, src, title, alt):
        # title must be quoted
        # ![alt](src "title")
        # if we have a config file
        # get_ctx().record_dependency(self.config_filename)

        url = urlparse(src)
        src = fix_src(url)
        if ":" not in alt:
            return super().image(src, title, alt)

        alt, rest = alt.split(":", 1)
        args, kwargs = parse_args(rest)
        style = "; ".join(f"{k}:{v}" for k, v in kwargs.items())
        cls = " ".join(args)
        attrs = [
            f'{attr}="{value}"'
            for attr, value in [
                ("style", style),
                ("class", cls),
                ("alt", alt),
                ("title", title),
            ]
            if value
        ]
        return f"""<img src="{src}" {' '.join(attrs)}/>"""

    def paragraph(self, text):
        # if we have a config file
        # get_ctx().record_dependency(self.config_filename)
        def shortcode(m):
            code = m.group(1).strip()
            args, kwargs = parse_args(code)
            cmd, *args = args
            # return f"<code>{cmd}: *{args}, **{kwargs}</code>"
            return render(cmd, args, kwargs)

        return super().paragraph(SHORTCODE.sub(shortcode, text))


class ShortcodesPlugin(Plugin):
    name = "shortcodes"
    description = "Embeds shortcodes in Markdown."

    def on_markdown_config(self, config, **extra):
        config.renderer_mixins.append(ShortcodesMixin)

