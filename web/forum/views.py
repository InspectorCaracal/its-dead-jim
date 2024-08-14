from django.shortcuts import (render, redirect, get_object_or_404)
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.utils.decorators import method_decorator
from django.db.models import Count
from django.urls import reverse

from django.views.generic import (UpdateView, ListView, DeleteView)
from django.utils import timezone

from web.forum.models import (Board, Category, Topic, Post, Poll, PollOption)
from web.forum.forms import (MultiChoicePoll, NewTopicForm, PostForm, SingleChoicePoll)

from switchboard import GENERAL_STOPWORDS, POSTS_PER_PAGE



def index(request):
    """This is the forum home."""

    categories = Category.objects.all()
    boards = [b for b in Board.objects.all() if b.account_permissions(request, 'view')]
    context = {'categories': categories, 'boards': boards, "page_title":"Forums"}

    # check if logged-in
    recent_activity = Topic.objects.filter(board__in=boards).order_by("-last_updated")
    if not request.user.is_anonymous:
        # NOTE: wow I hate this solution but maybe it's the best one??
        recent_activity = recent_activity.filter(posts__in=Post.objects.exclude(seen_by=request.user)).distinct()
    context['recent_activity'] = recent_activity[:5]

    #for acc in Accounts.objects.all():
     #   if acc.ndb.recent_forum_activity:
      #      context['recently_active_accounts'].append(acc)
    # NOT SURE I WANT TO ADD RECENTLY ACTIVE ACCOUNTS, BUT IT WOULDN"T BE NECESSARY TO DO A DB MIGRATION, AT LEAST
    # SO WILL LEAVE THIS FOR NOW


    return render(request, 'forum/index.html', context)

@login_required
def do_vote(request, poll_pk):
    print(f"voting for poll id {poll_pk}")
    poll = get_object_or_404(Poll, pk=poll_pk)
    post = poll.post
    topic = post.topic
    board = topic.board

    if poll.single_choice:
        form_class = SingleChoicePoll
    else:
        form_class = MultiChoicePoll

    if request.method == 'POST':
        form = form_class(request.POST, poll=poll)
        if form.is_valid():
            if poll.can_vote(request.user):
                # this user hasn't voted yet, they can do so
                poll.add_vote(request.user, request.POST.getlist('options'))
    else:
        form = form_class()
    return redirect('topic_posts', slug=board.slug, topic_pk=topic.pk)


class TopicListView(ListView):
    model = Topic
    context_object_name = 'topics'
    template_name = 'forum/topics.html'
    paginate_by = POSTS_PER_PAGE

    def get_context_data(self, **kwargs):
        kwargs['board'] = self.board
        kwargs["page_title"] = f"Forums: {self.board.name}"
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        self.board = get_object_or_404(Board, slug=self.kwargs.get('slug'))
        queryset = self.board.topics.order_by('-pinned', '-last_updated').annotate(replies=Count('posts') - 1)
        return queryset


class PostListView(ListView):
    model = Post
    context_object_name = 'posts'
    template_name = 'forum/topic_posts.html'
    paginate_by = POSTS_PER_PAGE

    def get_context_data(self, **kwargs):
        session_key = 'viewed_topic_{}'.format(self.topic.pk)

        kwargs['topic'] = self.topic
        kwargs["page_title"] = f"Forums: {self.topic.subject}"
        #if self.request.method == "POST":
            #print(f"we're printing this post for some reason: {self.request.POST}")
        context = super().get_context_data(**kwargs)

        if not self.request.user.is_anonymous:
            for post in context['object_list']:
                post.seen_by.add(self.request.user)

        if not self.request.session.get(session_key, False):
            self.topic.views += 1
            self.request.session[session_key] = True

        # handle the poll stuff
        if poll := self.topic.poll():
            if poll.can_vote(self.request.user):
                if poll.single_choice:
                    form_class = SingleChoicePoll
                else:
                    form_class = MultiChoicePoll

                context['form'] = form_class(poll=poll)
       
        return context

    def get_queryset(self):
        self.topic = get_object_or_404(Topic, board__slug=self.kwargs.get('slug'), pk=self.kwargs.get('topic_pk'))
        queryset = self.topic.posts.order_by('created_at')
        return queryset


@login_required
def new_topic(request, slug):
    """This is when you try to post a new topic in a board."""

    board = get_object_or_404(Board, slug=slug)
    user = request.user

    if request.method == 'POST':
        form = NewTopicForm(request.POST)
        if form.is_valid():

            topic = form.save(commit=False)
            topic.board = board
            topic.starter = user

            topic.save()
            content = form.cleaned_data.get('content')
            post = Post.objects.create(
                subject=topic.subject,
                post_number=1,
                content=content,
                topic=topic,
                created_by=user,
            )

            # We need to check if there's a poll...
            html_form_data = request.POST
            poll = html_form_data['poll_enabled']
            if poll == "yes":
                num_options = html_form_data["number_options"]
                poll_type = html_form_data["poll_type"]
                question = html_form_data["poll_question"]
                poll = Poll.objects.create(
                    post=post,
                    single_choice= poll_type == 'single-choice',
                    name=question,
                )
                for num in range(1, int(num_options)+1):
                    poll_option_num = num
                    poll_option_desc = html_form_data[f"option_{num}_text"]
                    option = PollOption.objects.create(
                        poll=poll,
                        name=poll_option_num,
                        description=poll_option_desc
                    )
                    option.save()
                poll.save()

            post.seen_by.add(user)
            return redirect('topic_posts', slug=board.slug, topic_pk=topic.pk)
    else:
        form = NewTopicForm()
    return render(request, 'forum/new_topic.html', {'board': board, 'form': form, "page_title": "New Forum Post"})


@login_required
def reply_topic(request, slug, topic_pk, post_pk=None):

    topic = get_object_or_404(Topic, board__slug=slug, pk=topic_pk)
    # TODO: figure out how to have an OPTIONAL reply post
    # replied = get_object_or_404(Post, topic__pk=topic_pk, pk=post_pk)

    if topic.locked:
        return redirect('board', slug=slug)

    account = request.user

    reply_to = topic
    if post_pk:
        reply_to = get_object_or_404(Post, topic__pk=topic_pk, pk=post_pk)

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():

            topic.last_updated = timezone.now()
            post = form.save(commit=False)
            post.topic = topic
            post.created_by = request.user

            # if "puppet" in request.session.keys():
            #     char_id = request.session["puppet"]
            # else:
            #     char_id = None
            # if char_id:
            #     for character in characters:
            #         if character.id == char_id:
            #             posting_character = character
            #             post.posting_character = posting_character

            post.post_number = topic.posts.count() + 1
            post.save()

            topic_url = reverse('topic_posts', kwargs={'slug': slug, 'topic_pk': topic_pk})
            topic_post_url = '{url}?page={page}#{id}'.format(
                url=topic_url,
                id=post.pk,
                page=topic.get_page_count()
            )

            return redirect(topic_post_url)
    else:
        reply_subject = reply_to.subject
        if not reply_subject.startswith("Re: "):
            reply_subject = "Re: "+reply_subject
        form = PostForm(initial={'subject': reply_subject})

    context = {
        'topic': topic,
        'form': form,
        # 'characters': characters,
        "page_title": "New Forum Reply",
        'reply_to': reply_to,
    }

    return render(request, 'forum/reply_topic.html', context)



@login_required
def lock_topic(request, slug, topic_pk):
    topic = get_object_or_404(Topic, board__slug=slug, pk=topic_pk)

    if hasattr(request.user, 'puppet') and request.user.is_staff:
        if topic.locked:
            topic.locked = False
        else:
            topic.locked = True
        topic.save()

    return redirect('topic_posts', slug=slug, topic_pk=topic_pk)


@login_required
def pin_topic(request, slug, topic_pk):
    topic = get_object_or_404(Topic, board__slug=slug, pk=topic_pk)


    if hasattr(request.user, 'puppet') and request.user.is_staff:
        if topic.pinned:
            topic.pinned = False
        else:
            topic.pinned = True
        topic.save()

    return redirect('topic_posts', slug=slug, topic_pk=topic_pk)

@method_decorator(login_required, name='dispatch')
class PostUpdateView(UpdateView):
    model = Post
    template_name = 'forum/edit_post.html'
    pk_url_kwarg = 'post_pk'
    context_object_name = 'post'
    form_class = PostForm

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            return queryset
        else:
            return queryset.filter(created_by=self.request.user)

    def form_valid(self, form):
        post = form.save(commit=False)

        if post.topic.locked:
            return redirect('board', slug=post.topic.board.slug)

        post.updated_by = self.request.user
        post.updated_at = timezone.now()
        post.save()
        return redirect('topic_posts', slug=post.topic.board.slug, topic_pk=post.topic.pk)


@login_required
def delete_post(request, slug, topic_pk, post_pk):
    user = request.user
    post = get_object_or_404(Post, pk=post_pk)
    topic = post.topic

    if topic.locked:
        return redirect('board', slug=slug)

    if user != post.created_by and not user.is_staff:
        return redirect('topic_posts', slug=slug, topic_pk=topic_pk)
    if topic.posts.count() < 2:
        topic.delete()
        return redirect('forum_index')
    else:
        post.delete()
        return redirect('topic_posts', slug=slug, topic_pk=topic_pk)

@login_required
def quote_post(request, slug, topic_pk, post_pk):
    topic = get_object_or_404(Topic, board__slug=slug, pk=topic_pk)
    quoted = get_object_or_404(Post, topic__pk=topic_pk, pk=post_pk)


    if topic.locked:
        return redirect('board', slug=slug)

    characters = request.user.characters

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():

            topic.last_updated = timezone.now()
            topic.save()

            post = form.save(commit=False)
            post.topic = topic
            post.created_by = request.user


            post.quoted = quoted
            post.quoted_text = str(quoted.content)

            if "puppet" in request.session.keys():
                char_id = request.session["puppet"]

                for character in characters:
                    if character.id == char_id:
                        posting_character = character
                        post.posting_character = posting_character

            post.save()
            # updates topic properly

            # this is to come out at the end of the pages...
            topic_url = reverse('topic_posts', kwargs={'slug': slug, 'topic_pk': topic_pk})
            topic_post_url = '{url}?page={page}#{id}'.format(
                url=topic_url,
                id=post.pk,
                page=topic.get_page_count()
            )

            return redirect(topic_post_url)
    else:
        reply_subject = quoted.subject or topic.subject
        if not reply_subject.startswith("Re: "):
            reply_subject = "Re: "+reply_subject
        form = PostForm(initial={'subject': reply_subject})

    return render(request, 'forum/quote_topic.html', {'topic': topic,
                                                      'form': form,
                                                      'quoted': quoted,
                                                      'characters':characters,
                                                      "page_title": "New Forum Reply"})


class SearchResultsView(ListView):
    model = Post
    template_name = 'forum/search_results.html'
    paginate_by = POSTS_PER_PAGE

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = f"Forum Search"
        kwargs['search_string'] = self.request.GET.get('q')
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        query = self.request.GET.get('q')
        board = self.request.GET.get('b')

        if len(query) <= 3:
            messages.error(self.request, "Your search term is too short.")
            return []

        if query.lower() in GENERAL_STOPWORDS:
            messages.error(self.request, "Your search term is too general.")
            return []
        
        #object_list = Post.objects.filter(
        #    Q(__icontains=query) | Q(content__icontains=query)
        #)
        if board:
            object_list = Post.objects.filter(topic__board__slug=board, content__icontains=query)
        else:
            object_list = Post.objects.filter(content__icontains=query)

        return object_list.order_by('-created_at')
