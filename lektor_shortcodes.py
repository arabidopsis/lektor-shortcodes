# -*- coding: utf-8 -*-
import re
import os
from copy import deepcopy
from lektor.pluginsystem import Plugin
from lektor.context import get_ctx
from lektor.markdown import Markdown
from lektor.db import F
from jinja2 import TemplateNotFound
from jinja2.filters import environmentfilter, do_truncate
from markupsafe import escape
from werkzeug.urls import url_parse
from datetime import datetime
from markupsafe import Markup
import click


local_timezone = datetime.utcnow().astimezone().tzinfo


# see https://github.com/lektor/lektor-markdown-highlighter/blob/master/lektor_markdown_highlighter.py
# for case where we need to register dependencies

SHORTCODE = re.compile(r"{{(.*?)}}")

QUOTES = re.compile(r"""(?:"([^"]*?)"|'([^']*?)')""")


@environmentfilter
def shorten(env, text, *args, **kwargs):
    if isinstance(text, Markdown):
        text.source = do_truncate(env, text.source, *args, **kwargs)
    elif isinstance(text, Markup):
        # text = Markup(do_truncate(env, text, *args, **kwargs))
        pass
    else:
        text = do_truncate(env, text, *args, **kwargs)
    return text


def page_slugs(c):
    if "@" not in c.path:
        return [c["_slug"]]
    s = c.path.split("@")
    return [*s[:-1], "page", s[-1]]


def mergedict(d, **kwargs):
    return {**d, **kwargs}


def split(s, sep=None):  # pylint: disable=unused-variable
    return [] if not s else (s.split(sep) if sep is not None else s.split())


def tostyles(d):
    def csskey(k):
        return k.replace("_", "-").lower()

    return ";".join(f"{csskey(k)}:{str(v)}" for k, v in d.items())


def toargs(d):
    return "&".join(f"{k}={str(v)}" for k, v in d.items())


def lastmod(record, format=None):
    if record.is_attachment:
        fn = record.attachment_filename
    else:
        fn = record.source_filename
    mtime = os.stat(fn).st_mtime
    dt = datetime.fromtimestamp(mtime, tz=local_timezone)
    if format:
        return dt.strftime(format)
    return dt.isoformat()


def add_script(record, src, embed=False, **kwargs):
    if not hasattr(record, "_js"):
        record._js = dict(links={}, embed={})
    if embed:
        js = record._js["embed"]
        js[src] = True
    else:
        js = record._js["links"]
        js[src] = kwargs.get("async", False)
    return ""


def gen_js(record):
    if not record or not hasattr(record, "_js"):
        return ""
    js = record._js
    ret = []
    for src, async_ in js["links"].items():
        s = f'<script src="{escape(src)}"{" async" if async_ else ""}></script>'
        ret.append(s)
    for src in js["embed"]:
        s = "<script>{src}</script>"
        ret.append(s)
    return Markup("\n".join(ret))


def parse_args(s):
    # we need to deal with spaces in quoted strings
    # so we convert all quoted strings to a token '####{i}####'
    # that has no spaces
    quoted = {}

    def map_quotes(m):
        i = len(quoted)
        k = f"#######{i}#######"
        quoted[k] = m.group(1) or m.group(2)
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
            return f"[no lektor build context for {cmd}]"
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
        return f'[could not find "shortcode/{cmd}.html" template]'


_prefix_re = re.compile(r"^\s*(!{1,4})\s+")

CLASSES = {
    1: "success",
    2: "info",
    3: "warning",
    4: "danger",
}

C = """<div class="alert alert-{}">
{}
</div>"""

# see https://github.com/lektor/lektor-markdown-admonition/blob/master/lektor_markdown_admonition.py
class AdmonitionMixin:
    def paragraph(self, text):
        match = _prefix_re.match(text)
        if match is None:
            return super().paragraph(text)
        level = len(match.group(1))
        return C.format(CLASSES[level], text[match.end() :],)


A = re.compile("^@([0-9]+)$")


def shortcode(m):
    code = m.group(1).strip()
    args, kwargs = parse_args(code)
    cmd, *args = args
    # return f"<code>{cmd}: *{args}, **{kwargs}</code>"
    return render(cmd, args, kwargs)


N = re.compile("w-[^0-9]*([0-9]+)$")


def get_width(classes, kwargs):
    if "width" in kwargs:
        width = kwargs["width"]
        if width.endswith("px"):
            width = width[:-2]
        if width.isdigit():
            return int(width)
    width = [w for w in classes if w.startswith("w-")]
    if not width:
        return 1
    w = width[0]
    m = N.match(w)
    if not m:
        return 1
    return int(m.group(1)) / 100.0


class ShortcodesMixin:
    name = "Markdown Shortcodes"
    description = "Embeds shortcodes in Markdown."

    SEP = ":"
    IMG_WIDTH = 800
    SHORTCODE = SHORTCODE

    def image(self, src, title, alt):
        # title must be quoted
        # ![alt](src "title")
        # if we have a config file
        # get_ctx().record_dependency(self.config_filename)
        def getsrc(path):
            return self.record.url_to("!" + path, base_url=get_ctx().base_url)

        att = A.match(src)
        if not att and self.SEP not in alt:
            return super().image(src, title, alt)

        alt, rest = alt.split(self.SEP, 1)
        args, kwargs = parse_args(rest)
        width = get_width(args, kwargs)
        img = None
        if self.record is not None:
            if att:
                n = int(att.group(1))
                img = self.record.attachments.images.offset(n - 1).limit(1).first()
            else:
                url = url_parse(src)
                if not url.scheme:
                    p = src if src.startswith("/") else "/" + src
                    img = self.record.attachments.images.filter(
                        (F._path == p) | (F.description == src)
                    ).first()
            if img:
                if width > 1:  # from width=30px kwargs
                    img = img.thumbnail(width=width)
                else:
                    img = img.thumbnail(width=self.IMG_WIDTH * width)
                src = getsrc(img.url_path)

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

    def link(self, link, title, text):
        if not self.SEP in text:
            return super().link(link, title, text)
        text, rest = text.split(self.SEP, 1)
        args, kwargs = parse_args(rest)
        if self.record is not None:
            url = url_parse(link)
            if not url.scheme:
                link = self.record.url_to("!" + link, base_url=get_ctx().base_url)

        link = escape(link)
        style = tostyles(kwargs)
        cls = " ".join(args)
        attrs = [
            f'{attr}="{value}"'
            for attr, value in [
                ("style", style),
                ("class", cls),
                ("title", escape(title) if title else ""),
            ]
            if value
        ]
        return f"""<a href="{link}" {' '.join(attrs)}/>{text}</a>"""

    def paragraph(self, text):
        # if we have a config file
        # get_ctx().record_dependency(self.config_filename)

        return super().paragraph(self.SHORTCODE.sub(shortcode, text))

    def text(self, text):
        t = self.SHORTCODE.sub(shortcode, text)
        if t == text:
            return super().text(text)
        return self.inline_html(t)


class ReadMore:
    def __init__(self, config):
        self.config = config
        self.display_link = config.get("display_link", "no").lower() in {
            "true",
            "1",
            "y",
            "yes",
        }

    def spilt_text(self, split=None):
        split_text = (
            split if split is not None else self.config.get("split_text", "---")
        )
        split_text = "\n{}\n".format(split_text)
        return split_text

    def link_text(self, post, link):
        link_text = self.config.get("link_text", "<br/>[{TEXT}]({URL_PATH})")
        text = link if isinstance(link, str) else "Read Full Post"
        # ctx = get_ctx()
        # url = ctx.url_to(post)
        link_text = link_text.format(URL_PATH=post.url_path, TEXT=text)
        return link_text

    def process_post(self, post, key="body", link=True, split=None):
        # body_type = post.datamodel.field_map[key].type.name
        body = post._data[key]

        skey = f"{key}_short"

        text_full = body.source

        split_text = self.spilt_text(split)
        contains_split = split_text in text_full
        if contains_split:
            short = deepcopy(body)
            split = text_full.split(split_text, 1)
            short.source = split[0]
            post._data[skey] = short
            body.source = "\n\n".join(split)

            if link or self.display_link:
                short.source += self.link_text(post, link)

        return post

    def __call__(self, post, key="body", link=True, split=None):
        return self.process_post(post, key, link, split=split)


class ShortcodesPlugin(Plugin):
    name = "shortcodes"
    description = "Embeds shortcodes in Markdown."

    def on_markdown_config(self, config=None, extra_flags=None):
        # click.secho(f"markdownconfig {config}", fg='yellow', bold=True)
        if config:

            class M(ShortcodesMixin):
                SEP = self.md_config["SEP"]
                IMG_WIDTH = self.md_config["IMG_WIDTH"]
                SHORTCODE = self.md_config["SHORTCODE"]

            config.renderer_mixins.append(M)
            config.renderer_mixins.append(AdmonitionMixin)

        return extra_flags

    def on_before_build(self, builder, build_state, source, prog, extra_flags=None):
        if source and hasattr(source, "_js"):
            del source._js
        return extra_flags

    # def on_after_build(self, builder, build_state, source, prog, extra_flags=None):
    #     if isinstance(source, Page):
    #         if source._shortcodes:
    #             print("end", source.path, source._shortcodes)
    #         del source._shortcodes
    #     return extra_flags

    # def update_markdown(self):
    #     for k,v in self.md_config.items():
    #         setattr(ShortcodesMixin,k,v)

    def patch(self, settings):
        sep = settings.get("separator")
        if sep:
            sep = sep.strip()
        else:
            sep = ShortcodesMixin.SEP

        width = settings.get("img_width")
        if width:
            width = int(width) if width.isdigit() else None
        else:
            width = ShortcodesMixin.IMG_WIDTH

        shortcode = settings.get("shortcode")
        if shortcode:
            shortcode = re.compile(shortcode)
        else:
            shortcode = ShortcodesMixin.SHORTCODE
        self.md_config = dict(SEP=sep, IMG_WIDTH=width, SHORTCODE=shortcode)

    def on_setup_env(self, extra_flags=None):
        # maybe on process-template-context context, values
        import requests

        config = self.get_config()
        self.patch(config)

        # session = requests.Session()
        def get_json(url, params, **kwargs):
            return requests.get(url, params=params, **kwargs).json()

        # for e.g. tweet shortcode
        self.env.jinja_env.globals["json_request"] = get_json
        # e.g kwargs | mergedict(a=1, c=2)
        # because we can't do {**kwargs, a:1, c:2}
        self.env.jinja_env.filters.update(
            {
                "mergedict": mergedict,
                "page_slugs": page_slugs,
                "lastmod": lastmod,
                "shorten": shorten,
                "readmore": ReadMore(config.section_as_dict("readmore")),
                "add_script": add_script,
                "gen_js": gen_js,
                "tostyles": tostyles,
                "toargs": toargs,
                "split": split,
            }
        )

        click.secho(f"shortcodes initialised!", fg="green", bold=True)
        return extra_flags
