# shortcodes

Add Hugo style "shortcodes" to lektor e.g.

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
`{**kwargs, args:args, kwargs:kwargs}`.

Short codes are meant to be *short* You can change the braces using
`shortcodes` configuration variable.

For example for the `shortcodes/youtube.html` you might have for
bootstrap:

```html
<div class="embed-responsive embed-responsive-16by9 {{args[1:]|join(' ')}}">
<iframe
    src="https://www.youtube.com/embed/{{args[0]}}"
    class="embed-responsive-item"
    allow="accelerometer; autoplay; clipboard-write;
          encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen>
</iframe>
</div>
```

A sufficiently modern css framework should permit you to style any shortcode
with simple class names.

## Images

Also parses images viz: `![Alt text: a b c width=30px](url "title text")`.
After a colon in the alt text all positional arguments are interpreted as classes
and keyword arguments are interpreted as style parameters.

You can alter the special separator (here `:`) in `configs/shortcodes.ini`:

```ini

separator = @
img_width = 800
# don't do scaling
img_width = none
# expects a single grouping representing the body of the short code
shortcodes = {{(.*?)}}
```

Also checks for `is_dark_theme` in
the `[theme_settings]` section of the
project file

## Installation

place this package in the directory packages maybe with

```bash
git submodule add https://github.com/arabidopsis/lektor-shortcodes.git packages/shortcodes
lektor plugins reinstall
```
