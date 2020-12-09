import os
import re
from datetime import datetime

import click
import requests
from jinja2 import TemplateNotFound
from jinja2.filters import do_truncate, environmentfilter
from lektor.context import get_ctx
from lektor.db import F
from lektor.markdown import Markdown
from lektor.pluginsystem import Plugin
from markupsafe import Markup, escape
from mistune import BlockLexer
from werkzeug.urls import url_parse

from .readmore import ReadMore

local_timezone = datetime.utcnow().astimezone().tzinfo


# see https://github.com/lektor/lektor-markdown-highlighter/blob/master/lektor_markdown_highlighter.py
# for case where we need to register dependencies


# jinja filters --------------------


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
    return [] if not s else str(s).split(sep)


def tostyles(d):
    def csskey(k):
        return k.replace("_", "-").lower()

    return ";".join(f"{csskey(k)}:{str(v)}" for k, v in d.items())


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


def add_script(
    record, src, embed=False, template=False, jquery=True, css=False, **kwargs
):
    src = src.strip()
    if not src:
        return ""
    if not hasattr(record, "_js"):
        record._js = dict(links={}, embed={}, templates={}, css={})
    J = record._js
    if css:
        d = J["css"]
        d[src] = True
    elif embed:
        js = J["embed"]
        if jquery:
            src = "jQuery(function($) { %s })" % src
        js[src] = True
    elif template:
        js = J["templates"]
        js[src] = True
    else:
        js = J["links"]
        js[src] = kwargs.get("async", False)
    return ""


def gen_js(record):
    ctx = get_ctx()

    def js_template(name):
        t = """<script>{%% include "%s" %%}</script>""" % name
        return ctx.env.jinja_env.from_string(t).render()

    if not record or not hasattr(record, "_js"):
        return ""
    js = record._js
    ret = []
    for src in js["css"]:
        js["templates"]["shortcodes/add_css.js"] = True
        js["embed"][f'API.add_css("{escape(src)}")'] = True
        # FIXME place this in head
        # s = f'<link rel="stylesheet" href="{escape(src)}"/>'
        # ret.append(s)

    for src, async_ in js["links"].items():
        s = f'<script src="{escape(src)}"{" async" if async_ else ""}></script>'
        ret.append(s)
    for src in js["templates"]:
        try:
            s = js_template(src)
        except TemplateNotFound:
            s = f"[shortcode template {src} not found]"
        ret.append(s)

    for src in js["embed"]:
        s = f"<script>{src}</script>"
        ret.append(s)

    return Markup("\n".join(ret))


QUOTES = re.compile(r"""(?:"([^"]*?)"|'([^']*?)')""", re.DOTALL)

FLOAT = re.compile(r"^[+-]?[0-9]*\.[0-9]+$")


def parse_args(sargs):
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
        if FLOAT.match(v):
            return float(v)
        return v

    s = QUOTES.sub(map_quotes, sargs)
    args = s.split()  # now we can split
    kwargs = dict(a.split("=", 1) for a in args if "=" in a)
    args = [a for a in args if "=" not in a]
    kwargs = {fix_val(k): fix_val(v) for k, v in kwargs.items()}
    args = [fix_val(v) for v in args]
    return args, kwargs


def render(cmd, args, kwargs):
    try:
        ctx = get_ctx()
        values = {**kwargs, "args": args, "kwargs": kwargs}
        return ctx.env.render_template(
            [f"shortcodes/{cmd}.html", "shortcode/default.html"],
            pad=ctx.pad,  # site object
            this=ctx.record,  # source object
            values=values,
        )
    except TemplateNotFound:
        # this is what lektor does with flow blocks...
        return Markup(f'[could not find "shortcode/{cmd}.html" template]')


def shortcode(m):
    code = m.group(1).strip()
    args, kwargs = parse_args(code)
    cmd, *args = args
    return render(cmd, args, kwargs)


class ShortcodeLexer(BlockLexer):
    def __init__(self, regexp, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rules.shortcode = regexp
        if "shortcode" not in self.default_rules:  # class list
            self.default_rules.insert(1, "shortcode")

    def parse_shortcode(self, match):
        self.tokens.append({"type": "close_html", "text": shortcode(match)})


_prefix_re = re.compile(r"^\s*(!{1,4})\s+")

CLASSES = {
    1: "note",
    2: "info",
    3: "tip",
    4: "warning",
}
FA = {
    1: "sticky-note",
    2: "info-circle",
    3: "candy-cane",
    4: "exclamation-triangle",
}

C = """
<div class="card admonition admonition-{cls} mb-1">
  <div class="card-header"><i class="fas fa-{fa}"></i> {header}:</div>
  <div class="card-body">{body}</div>
</div>"""

# see https://github.com/lektor/lektor-markdown-admonition/blob/master/lektor_markdown_admonition.py


class AdmonitionMixin:
    def paragraph(self, text):
        match = _prefix_re.match(text)
        if match is None:
            return super().paragraph(text)
        level = len(match.group(1))
        cls = CLASSES[level]
        return C.format(
            cls=cls, fa=FA[level], header=cls.title(), body=text[match.end() :]
        )


PAGE_NUM = re.compile("^@([0-9]+)$")


BOOTSTRAP_WIDTH = re.compile("^w(?:([0-9]+)|-(?:[a-z-]+)?([0-9]+))$")


def get_width(classes, kwargs):
    if "width" in kwargs:
        width = kwargs["width"]
        if width.endswith("px"):
            width = width[:-2]
        if width.isdigit():
            return int(width)

    for w in [w for w in classes if w.startswith("w")]:
        m = BOOTSTRAP_WIDTH.match(w)
        if m:
            v = m.group(1) or m.group(2)
            return int(v) / 100.0
    return 1


class ShortcodesMixin:

    SEP = ":"
    IMG_WIDTH = 800
    SHORTCODE = re.compile(r"{{(.*?)}}", re.DOTALL)

    def image(self, src, title, alt):
        # title must be quoted
        # ![alt](src "title")
        # if we have a config file
        # get_ctx().record_dependency(self.config_filename)

        def getsrc(path):
            return self.record.url_to("!" + path, base_url=get_ctx().base_url)

        att = PAGE_NUM.match(src)
        if not att and self.SEP not in alt:
            return super().image(src, title, alt)

        alt, rest = alt.rsplit(self.SEP, 1)
        args, kwargs = parse_args(rest)

        if self.record:
            img = None
            width = get_width(args, kwargs)
            if att:
                n = int(att.group(1))
                img = self.record.attachments.images.offset(n - 1).limit(1).first()
            else:
                url = url_parse(src)
                if not url.scheme:
                    img = self.record.attachments.images.filter(
                        (F._id == src) | (F.description == src)
                    ).first()

            if img:
                if width > 1:  # from width=30px kwargs
                    img = img.thumbnail(width=width)
                else:
                    img = img.thumbnail(width=self.IMG_WIDTH * width)
                src = getsrc(img.url_path)

        src = escape(src)
        alt = escape(alt)
        style = escape(tostyles(kwargs))
        title = escape(title) if title else ""
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

    def link(self, link, title, text):
        # we have to watch out for
        # [<i style="color:blue"></i>](link)
        if self.SEP not in text:
            return super().link(link, title, text)
        ltext, rest = text.rsplit(self.SEP, 1)
        if ">" in rest:
            # probably something like style="color:blue" in original text
            return super().link(link, title, text)

        args, kwargs = parse_args(rest)
        if self.record is not None:
            url = url_parse(link)
            if not url.scheme:
                link = self.record.url_to("!" + link, base_url=get_ctx().base_url)

        attrs = {}
        download = ""

        if "-new-tab" in args:
            args.remove("-new-tab")
            attrs["target"] = "_blank"
            attrs["rel"] = "noreferrer noopener"  # from MDN
        if "download" in args:
            args.remove("download")
            download = " download"
        if "target" in kwargs:
            attrs["target"] = kwargs.pop("target")
            attrs["rel"] = "noreferrer noopener"  # from MDN
        link = escape(link)
        style = escape(tostyles(kwargs))
        cls = " ".join(args)
        attrs = [
            f'{attr}="{value}"'
            for attr, value in [
                ("style", style),
                ("class", cls),
                ("title", escape(title) if title else ""),
                *list(attrs.items()),
            ]
            if value
        ]
        return f"""<a href="{link}"{download} {' '.join(attrs)}/>{ltext}</a>"""

    # def paragraph(self, text):
    #     # if we have a config file
    #     # get_ctx().record_dependency(self.config_filename)

    #     return super().paragraph(self.SHORTCODE.sub(shortcode, text))

    def text(self, text):
        t = self.SHORTCODE.sub(shortcode, text)
        if t == text:
            return super().text(text)
        return self.inline_html(t)


class ShortcodesPlugin(Plugin):
    name = "shortcodes"
    description = "Embeds shortcodes in Markdown."

    def on_markdown_config(self, config=None, extra_flags=None):
        # click.secho(f"markdownconfig {config}", fg='yellow', bold=True)
        if config:
            config.renderer_mixins.extend(
                [self.md_config["ShortcodesMixin"], AdmonitionMixin]
            )
            # also for inline
            config.options["block"] = ShortcodeLexer(self.md_config["SHORTCODE"])

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

    def make_md_config(self, settings):
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

        config = self.get_config()
        self.make_md_config(config)

        class M(ShortcodesMixin):
            SEP = self.md_config["SEP"]
            IMG_WIDTH = self.md_config["IMG_WIDTH"]
            SHORTCODE = self.md_config["SHORTCODE"]

        self.md_config["ShortcodesMixin"] = M

        actions = config.section_as_dict("actions")

        def action_url(action):
            if action not in actions:
                return action
            return actions[action]

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
                "split": split,
                "action_url": action_url,
            }
        )

        t = datetime.now().isoformat()
        # path = os.environ.get("PATH")

        click.secho(f"shortcodes initialised @ {t}", fg="green", bold=True)
        return extra_flags
