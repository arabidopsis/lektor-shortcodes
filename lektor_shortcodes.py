# -*- coding: utf-8 -*-
import re
from lektor.pluginsystem import Plugin
from lektor.context import get_ctx
from lektor.db import Page
from jinja2 import TemplateNotFound
from markupsafe import escape
from werkzeug.urls import url_parse

# see https://github.com/lektor/lektor-markdown-highlighter/blob/master/lektor_markdown_highlighter.py
# for case where we need to register dependencies

SHORTCODE = re.compile(r"{{\s*(.*?)\s*}}")

QUOTES = re.compile(r'"([^"].*?)"')


def parse_args(s):
    # we need to deal with spaces in quoted strings
    # so we convert all quoted strings to a token '####{i}####'
    # that has no space
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
    args = s.split()  # now we can split
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
        values = {**kwargs, "args": args, "kwargs": kwargs}
        # ctx.record._shortcodes[cmd] = values
        return ctx.env.render_template(
            [
                f"shortcodes/{cmd}.html",
                # "blocks/default.html",
            ],
            pad=ctx.pad,  # site object
            this=ctx.record,  # source object
            values=values,
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

        if ":" not in alt:
            return super().image(src, title, alt)

        alt, rest = alt.split(":", 1)
        args, kwargs = parse_args(rest)
        if self.record is not None:
            url = url_parse(src)
            if not url.scheme:
                src = self.record.url_to("!" + src, base_url=get_ctx().base_url)
        src = escape(src)
        alt = escape(alt)
        style = "; ".join(f"{k}:{v}" for k, v in kwargs.items())
        cls = " ".join(args)
        attrs = [
            f'{attr}="{value}"'
            for attr, value in [
                ("style", style),
                ("class", cls),
                ("alt", alt),
                ("title", escape(title) if title else ""),
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

def page_slugs(c):
    if '@' not in c.path:
        return [c['_slug']]
    s = c.path.split('@')
    return [*s[:-1], 'page', s[-1]]

class ShortcodesPlugin(Plugin):
    name = "shortcodes"
    description = "Embeds shortcodes in Markdown."

    def on_markdown_config(self, config, **extra):
        config.renderer_mixins.append(ShortcodesMixin)

    # def on_before_build(self, builder, build_state, source, prog, **extra):
    #     if isinstance(source, Page):
    #         source._shortcodes = {}

    # def on_after_build(self, builder, build_state, source, prog, **extra):
    #     if isinstance(source, Page):
    #         if source._shortcodes:
    #             print("end", source.path, source._shortcodes)
    #         del source._shortcodes

    def on_setup_env(self, **extra):
        # maybe on process-template-context context, values
        import requests

        # session = requests.Session()
        def get_json(url, params, **kwargs):
            return requests.get(url, params=params, **kwargs).json()

        self.env.jinja_env.globals["json_request"] = get_json
        # e.g kwargs | mergedict(a=1, c=2)
        # because we can't do {**kwargs, a:1, c:2}
        self.env.jinja_env.filters["mergedict"] = lambda d, **kwargs: {**d, **kwargs}
        self.env.jinja_env.filters["page_slugs"] = page_slugs

