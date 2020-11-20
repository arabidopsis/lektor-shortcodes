from copy import deepcopy


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
        split_text = f"\n{split_text}\n"
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
        return self.process_post(post, key=key, link=link, split=split)
