# shortcodes

Add Hugo style "shortcodes" to lektor e.g.

`{{ youtube rXZGDADbdad w-50 float-right m-2 }}`

This requires a template `youtube.html` in the `shortcodes` directory
of your templates folder. Positional arguments will be passed to
the template in the variable `args`.

Currently no argument checking is done so the template should be
very defensive and have defaults for all the keyword arguments.

Also only double quotes `"` are understood if you have space separated arguments.
Keys *can't* have spaces.

For example for the `shortcodes/youtube.html` you might have:

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

## Images

Also parses images viz: `![Alt text: a b c width=30px](url "title text")`.
After a colon in the alt text all positional arguments are interpreted as classes
and keyword arguments are interpreted as style parameters.

You can alter the special separator (here `:`) in `configs/shortcodes.ini`:

```ini

separator = @
img_width = 400
# don't do scaling
img_width = none
shortcodes = {{(.*?)}}
is_dark_theme = true
```

## Installation

place this package in the directory packages maybe with

```bash
git submodule add https://github.com/arabidopsis/lektor-shortcodes.git packages/shortcodes
lektor plugins reinstall
```
