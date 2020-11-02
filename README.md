# shortcodes

Add Hugo style "shortcodes" to lektor e.g.

`{{ youtube rXZGDADbdad width=50% height=300 position=left }}`

This requires a template `youtube.html` in the `shortcodes` directory
of your templates folder. Positional arguments will be passed to
the template in the variable `args`.

Currently no argument checking is done so the template should be
very defensive and have defaults for all the keyword arguments.

For example for the `shortcodes/youtube.html` you might have:

```html

<iframe
    {% if class %} class="{{class}}"{% endif %}
    {% if position %} style="float:{{position}}"{% endif %}
    width="{{width|default(560)}}"
    height="{{height|default(315)}}"
    src="https://www.youtube.com/embed/{{args[0]}}"
    frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen>
</iframe>

```

## Images

Also parses images viz: `![Alt text: a b c width=30px](url "title text")`.
After a colon in the alt text all positional arguments are interpreted as classes
and keyword arguments are interpreted as style parameters.

## Installation

place this package in the directory packages maybe with

```bash
git submodule add https://github.com/arabidopsis/lektor-shortcodes.git packages/shortcodes
lektor plugins reinstall
```
