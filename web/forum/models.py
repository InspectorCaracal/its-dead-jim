from django.db import models
from django.utils.text import Truncator
import math, random
from switchboard import POSTS_PER_PAGE

class Category(models.Model):
    """
    This is a forum category. It will be listed in the forum index and serve as a container for
    different types of forums. Categories may have different permissions and rules reflected in
    the code...
    """

    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=100)


    class Meta(object):
        "Define Django meta options"
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    
    def get_boards(self):
        return Board.objects.filter(category=self)


class Board(models.Model):
    """
    The regular type of board. We want to track how many posts it has so we can separate them
    into pages...
    """

    name = models.CharField(max_length=30, unique=True)
    slug = models.CharField(max_length=30, unique=True, default=random.randint(1, 1000))
    description = models.CharField(max_length=100)
    category = models.ForeignKey(Category, related_name='boards', on_delete=models.CASCADE)

    permissions = models.CharField(max_length=200, default='reply:all, view:all, post:all')

    def __str__(self):
        return self.name

    def get_posts_count(self):
        return Post.objects.filter(topic__board=self).count()

    def get_last_post(self):
        return Post.objects.filter(topic__board=self).order_by('-created_at').first()

    def account_permissions(self, request, act):
        """ returns true if an account has permissions to view, else returns false """
        # todo: expand at some point, for organization-specific boards

        if hasattr(request.user, 'puppet'):
            perm_level = "admin" if request.user.is_staff else "all"
        else:
            perm_level = "all"

        permstrings = [a.strip() for a in self.permissions.split(",")]
        for perm_field in permstrings:
            if perm_field.startswith(act):
                permitted = perm_field.replace(f"{act}:", "").strip()
                if permitted == "admin":
                    return True if perm_level == "admin" else False
                elif permitted == "all":
                    return True
        # no permissions set for this act, for some reason? should default be true or false? let's say... true
        return True


class Topic(models.Model):
    """
    This will be a topic posted by an OP on a board.

    name = models.CharField(max_length=30, unique=False, default="topic")"""
    subject = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now_add=True)
    board = models.ForeignKey(Board, related_name='topics', on_delete=models.CASCADE)
    starter = models.ForeignKey("accounts.AccountDB", null=True, related_name="+", on_delete=models.SET_NULL)
    views = models.PositiveIntegerField(default=0)
    pinned = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)

    def form_view(self):
        return self.subject

    def get_last_five_posts(self):
        return self.posts.order_by('-created_at')[:5]

    def get_page_count(self):
        count = self.posts.count()
        pages = count / 10
        return math.ceil(pages)

    def has_many_pages(self, count=None):
        if count is None:
            count = self.get_page_count()
        return count > 6

    def get_page_range(self):
        count = self.get_page_count()
        if self.has_many_pages(count):
            return range(1, 5)
        return range(1, count + 1)

    def poll(self):
        post = self.get_first_post()
        if not post:
            return False
        return post.get_poll

    def get_last_post(self):
        return self.posts.order_by('-created_at').first()

    def get_first_post(self):
        return self.posts.order_by('-created_at').last()


    def __str__(self):
        return self.subject



class Post(models.Model):
    """
    This is a posted/reply comment on a topic.
    """
    subject = models.CharField(max_length=255, null=True)
    content = models.TextField(max_length=16000)
    topic = models.ForeignKey(Topic, related_name='posts', on_delete=models.CASCADE)
    post_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey("accounts.AccountDB", related_name='posts', null=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey("accounts.AccountDB", null=True, related_name='+', on_delete=models.SET_NULL)
    quoted = models.ForeignKey("Post", related_name='replies', null=True, on_delete=models.SET_NULL)
    quoted_text = models.TextField(max_length=16000)

    seen_by = models.ManyToManyField("accounts.AccountDB", null=True, related_name='posts_seen')

    @property
    def get_poll(self):
        self_polls = self.related_poll.all()
        if not self_polls:
            return None
        else:
            return list(self_polls)[0]

    def truncated_content(self):
        from bleach import clean
        stripped = clean(self.content,strip=True)
        truncated_message = Truncator(stripped).chars(30)
        return truncated_message

    def __str__(self):
        truncated_message = Truncator(self.content)
        return truncated_message.chars(30)

    def get_page_num(self):
        postcount = self.topic.posts.filter(created_at__lte=self.created_at).count()
        return ((postcount-1)//POSTS_PER_PAGE) + 1


class Poll(models.Model):
    #This will be attached to a post.

    name = models.CharField(max_length=300, unique=False, default="poll")
    post = models.ForeignKey(Post, related_name='related_poll', on_delete=models.CASCADE)
    single_choice = models.BooleanField(default=True)

    @property
    def list_options(self):
        options = self.options.all()
        return list(options)
    
    @property
    def total_votes(self):
        return sum([opt.num_voters for opt in self.options.annotate(num_voters=models.Count('voters'))])

    def can_vote(self, user):
        return PollOption.objects.filter(poll=self, voters=user).count() == 0

    def add_vote(self, user, option_list):
        voted = self.options.filter(pk__in=option_list)
        for opt in voted:
            opt.voters.add(user)
            opt.save()
    
    def remove_voter(self, user):
        for opt in self.list_options:
            opt.voters.remove(user)
            opt.save()

    def get_option_choices(self):
        return [ (opt.pk, opt.description) for opt in self.options.all()]

class PollOption(models.Model):
    #These will be attached to a poll.

    name = models.CharField(max_length=30, unique=False, default=1)
    description = models.CharField(max_length=80, unique=False, default=1)
    poll = models.ForeignKey(Poll, related_name='options', on_delete=models.CASCADE)
    voters = models.ManyToManyField("accounts.AccountDB", null=True, related_name='polls_voted')

    @property
    def percentage(self):
        #This returns a string that shows the percentage of the votes that go to this thing.
        percent = (self.voters.count() / (self.poll.total_votes or 1)) * 100
        p_display = f"{int(percent)}%"
        return p_display
