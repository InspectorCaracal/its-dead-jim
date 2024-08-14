"""
An in-game command for reading wiki articles from an integrated django-wiki app!

Adding django-wiki to your Evennia game: https://www.evennia.com/docs/latest/Howtos/Web-Add-a-wiki.html

For a typical Evennia game, you can just drop this directly into your gamedir and add it to your default
cmdset. After you've installed the wiki, of course!

## Article searching: YES

This works by taking the command args and running queries on the wiki's `Article` manager to check for
the args by title, then by content. It doesn't currently take into account the caller's read permissions,
but that should be reasonably easy to add in to `CmdWiki.search_article` if you don't want players able
to read all of the articles.

## Markdown formatting: MOSTLY NO

django-wiki uses markdown for its article formatting, so the article text will display in-game with the
markdown syntax. (Fortunately, one of the best features of markdown is that it's much more human-readable
than many other markup languages.) And while this `wiki` evennia command doesn't format normal markdown
markup, it will catch links!

## Clickable links: YES!

For internal wiki links, it replaces them with Evennia's clickable-command syntax.

    [[Getting Started]]

will become:

    |lcwiki Getting Started|ltGetting Started|le

For normal markdown links, it replaces them with Evennia's clickable-url syntax.

    [click me!](https://example.com)

will become:

    |luhttps://example.com|ltclick me!|le

"""

from core.commands import Command

import re
from django.db.models import Q
from wiki.models import Article

_RE_WIKILINKS = re.compile(r'\[\[(.*)\]\]')
_RE_MDLINKS = re.compile(r'\[([^\[\]]+?)\]\(([^\)]+?)\)')

class CmdWiki(Command):
    """
    Read an article from the wiki

    Usage:
      wiki <text>

    The command will search for articles on the game's wiki where the title or content
    contain the entered text.

    Example:
      wiki getting started
    
    If an article is titled "Getting Started", you will get that article.
    
    If there are two articles, "Getting Started: Part One" and "Getting Started: Part Two",
    you'll be told the titles of the two matches.
    
    If no titles match, but an article contains the words "getting started" in its content,
    you'll get that article as a result.
    
    If the input text appears nowhere in ANY wiki articles, there won't be any results.
    """

    key = "wiki"
    locks = "cmd:all()"

    def func(self):
        """Main command func"""
        self.args = self.args.strip()

        if not self.args:
            self.msg("Read which wiki page?")
            return

        if res := self.search_article(self.args):
            title, text = res
            self.msg(f"{title}\n\n{text}")


    def search_article(self, search_term):
        """
        Access function for searching for an article.
        
        Args:
          search_term (str) -  the text to search for
        
        Returns:
          (title, text) or None
        """
        results = self._build_query(search_term)
        
        return self.handle_results(results)


    def _build_query(self, search_term):
        """
        Builds a queryset based on the search arg
        
        Args:
					search_term (str) -  the string to look up
        
        Returns:
          articles (QuerySet)
        """
        # TODO: filter by read permissions?
        
        # check exact title match first
        if articles := Article.objects.filter(
            Q(current_revision__title__iexact=search_term)
        ):
            return articles

				# then, check by title
        if articles := Article.objects.filter(
            Q(current_revision__title__icontains=search_term)
        ):
            return articles
        
				# then and only then, check by contents
        articles = Article.objects.filter(
            Q(current_revision__content__icontains=search_term)
				)
        
				# this result gets handed back regardless of whether it's empty or not
        return articles


    def handle_results(self, results):
        """
        Handles the query set of matched articles, including error messaging.

        Args:
            results (QuerySet) -  The Articles which matched the input.

        Returns:
            (title, text) or None
        """
        match len(results):
            case 0:
                return self._no_matches()
            case 1:
                res = results[0]
                title = self.format_title(str(res))
                text = self.format_text(res)
                return (title, text)
            case _:
                return self._multiple_matches(results)


    def format_title(self, title):
        """Format the title text"""
        return f"# {title}"

    def format_content(self, text):
        """Format the article content text."""
        return self._parse_links(text)

    def _parse_links(self, article):
        """Replaces wikilinks with clickable wiki commands"""
        text = article.current_revision.content
        text = _RE_WIKILINKS.sub(r'\|lc\1\|lt\1\|le', text)
        text = _RE_MDLINKS.sub(r'\|lu\2\|lt\1\|le', text)
            
        return text


    def _no_matches(self):
        """Command feedback for no matches"""
        self.msg(f"There are no wiki pages matching '{self.args}'.")


    def _multiple_matches(self, results):
        """
        Command feedback for multiple matches
        
        Messages a list of matches, up to the top 5
        """
        article_list = []
        for res in results[:5]:
            name = str(res)
            name = f"- |lcwiki {name}|lt{name}|le"
            article_list.append(name)

        self.msg(f"Multiple articles match '{self.args}':\n" + "\n".join(article_list))
