# -*- coding: utf-8 -*-
import re
from lektor.pluginsystem import Plugin
from lektor.context import get_ctx
from jinja2 import TemplateNotFound


SHORTCODE = re.compile(r"{{\s*(.*?)\s*}}")

QUOTES = re.compile(r'["]([^"].*?)["]')


def parse_args(s):
    d = {}

    def f(m):
        i = len(d)
        k = f"#######{i}#######"
        d[k] = m.group(1)
        return k

    def fix_val(v):
        if v in d:
            return d[v]
        if v.isdigit():
            return int(v)
        return v

    s = QUOTES.sub(f, s)
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


class ShortcodesMixin:
    name = "Markdown Shortcodes"
    description = "Embeds shortcodes in Markdown."

    def paragraph(self, text):
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

