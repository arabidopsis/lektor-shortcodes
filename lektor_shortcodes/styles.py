# the class Styles is added to the global jinja2 template rendering state as "styles"
# see fragments/styles.css
from colour import Color as BaseColor

# from colour import color_scale


def clamp(c):
    return max(0.0, min(1.0, c))


def darken(c, delta):
    if not isinstance(c, Color):
        c = Color(c)
    return Color(c, luminance=clamp(c.luminance - delta))


def lighten(c, delta):
    if not isinstance(c, Color):
        c = Color(c)
    return Color(c, luminance=clamp(c.luminance + delta))


def saturate(c, delta):
    if not isinstance(c, Color):
        c = Color(c)
    return Color(c, saturation=clamp(c.saturation - delta))


def desaturate(c, delta):
    if not isinstance(c, Color):
        c = Color(c)
    return Color(c, saturation=clamp(c.saturation + delta))


class Color(BaseColor):
    def darken(self, delta):
        return darken(self, delta)

    def lighten(self, delta):
        return lighten(self, delta)

    def saturate(self, delta):
        return saturate(self, delta)

    def desaturate(self, delta):
        return desaturate(self, delta)

    def __call__(self, method, delta):
        return getattr(self, method)(delta)


if __name__ == "__main__":
    import sys

    print(Color(sys.argv[1])("darken", 0.2)("saturate", 0.2))
