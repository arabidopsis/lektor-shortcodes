# shortcodes

Adds -- among other things -- Hugo style "shortcodes" to lektor e.g.

`{{ youtube rXZGDADbdad w-50 float-right m-2 }}`

This requires a template `youtube.html` in the `shortcodes` directory
of your templates folder. Positional arguments will be passed to
the template in the variable `args`.

Currently no argument checking is done so the template should be
very defensive and have defaults for all the keyword arguments.

Keys *can't* have spaces.

The full code is:

`{{ command arg1 arg2 arg3 key1=value1 key2=value2 key3="a string with spaces" }}`

The plugin invokes a template of the name `shortcodes/{command}.html`
where the variables available will be the dictionary
`{**kwargs, args:args, kwargs:kwargs}`. (So if you have a key called `args` or `kwargs` you will have
to fish it out of kwargs e.g. `kwargs.kwargs` or `kwargs.args`)

Short codes are meant to be *short* You can change the braces using
`shortcodes` configuration variable.

For example for the `shortcodes/youtube.html` you might have for
bootstrap:

```html
<div class="embed-responsive embed-responsive-16by9 {{args[1:]|join(' ')}}"
    style="{{kwargs|tostyles}}">
<iframe
    src="https://www.youtube.com/embed/{{args[0]}}"
    class="embed-responsive-item"
    allow="accelerometer; autoplay; clipboard-write;
          encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen>
</iframe>
</div>
```

If your short code requires a javascript library then add say:

```jinja
{{this|add_script('https://platform.twitter.com/widgets.js', async=True)}}
```

to your shortcode template. Then in the main `page.html` add
a `{{ this|gen_js() }}` before the final `</body>` end tag. The js
will only be added if the short code was invoked on the page.

To embed some java script use:

```jinja
`{{this|add_script('window.myglobal = 2', embed=True, jquery=False)}}`
```

To add a javascript template use:

```jinja
`{{this|add_script("shortcodes/form_validation.js", template=True)}}`
```

A sufficiently modern css framework should permit you to style any shortcode
with simple class names.

## Images

Also parses images viz: `![Alt text: a b c width=30px](url "title text")`.
After a colon in the alt text all positional arguments are interpreted as classes
and keyword arguments are interpreted as style parameters.

You can alter the special separator (here `:`) in `configs/shortcodes.ini`:

```ini

separator = :
img_width = 800
# or don't do scaling
# img_width = none
# expects a single grouping representing the body of the short code
shortcodes = {{(.*?)}}

# contact forms
# {{contact-form action=honeybee }}
[actions]
honeybee = "https://honeybeehealthresearch.org/app/honeybee/contact-form"

```

## Read More

Usage:

```jinja
{{this|readmore(key='body', link='Read more At', split='--readmore--' ).body_short}}
```

Adds a `{key}_short` attribute to `this` which is the text
before the `split` text. It also removes the split text from the body.

Defaults for link and split can be set in the `[readmore]` section:

```ini
[readmore]
# globally display links -- overridden by argument
display_link = yes

# uses python format braces
link_text = '<br/>[{TEXT}]({URL_PATH})'
# or skip the text
link_text = '<br/>[Read More]({URL_PATH})'
# split on the first paragraph of just '---'
split_text = '---'

```

## Miscellaeneous Filters/Globals

The `-new-tab` argument for a link will create a `target="_blank"` on the link.

* `shorten`: uses `jinja2:truncate` but understands `Markdown` and `Markup` objects
* `mergedict`: e.g. `dict|mergedict(a=1,b=2)`. Same as `{**dict, a=1,b=2}`
* `tostyles`: turn a dictionary into a set of styles (changing keys into kebab case).
  e.g. `style="{{dict|tostyles}}"`
* `lastmod`: Last modification time of the source document e.g. `{{this|lastmod(format='%Y-%m-%d %H:%M')}}` default is
  isoformat.
* `json_request`: *not* a filter. Make a json request to a website e.g. used with the twitter
  short code.

For example `tweet.html` is:
  
```jinja
{# most useful are: align={left,right,center,none} theme={light,dark} #}
{% set is_dark_theme = config.THEME_SETTINGS.is_dark_theme == 'true' %}
{% set url = 'https://twitter.com/' + args[0] %}
{# omit_script so we place it at the end of the document #}
{% set params = kwargs | mergedict(url=url, dnt='true', omit_script='true', theme='dark' if is_dark_theme else 'light') %}
{{json_request('https://publish.twitter.com/oembed', params=params).html | safe}}
{{this | add_script('https://platform.twitter.com/widgets.js', async=True)}}
```

## Installation

place this package in the directory `packages` maybe with

```bash
git submodule add https://github.com/arabidopsis/lektor-shortcodes.git packages/shortcodes
# or just git clone ...
```

or add to `[packages]` section of project or theme

```ini
[packages]
https://github.com/arabidopsis/lektor-shortcodes/archive/main.tar.gz = ""
```

## Notes

Combined with say Tachyons we can do
things like:

`follow me on [{{fab twitter p-3 bg-pink br-100 f3 white align-middle shadow grow}}: -new-tab](https://twitter.com/mememe) OK!`
