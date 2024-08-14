# URL patterns for the character app
from django.urls import (path, re_path)
from web.forum.views import (index, new_topic, reply_topic, PostUpdateView, TopicListView, PostListView, delete_post,
                             quote_post, lock_topic, pin_topic, SearchResultsView, do_vote)

urlpatterns = [


    path('', index, name="forum_index"),

    re_path(r'vote/(?P<poll_pk>\d+)/$', do_vote, name='do_vote'),

    re_path(r'(?P<slug>[\w.@+-]+)/$', TopicListView.as_view(), name='board'),
    re_path(r'(?P<slug>[\w.@+-]+)/new/$', new_topic, name='new_topic'),
    re_path(r'(?P<slug>[\w.@+-]+)/topics/(?P<topic_pk>\d+)/$', PostListView.as_view(), name='topic_posts'),

    re_path(r'(?P<slug>[\w.@+-]+)/topics/(?P<topic_pk>\d+)/lock/$', lock_topic, name='lock_topic'),
    re_path(r'(?P<slug>[\w.@+-]+)/topics/(?P<topic_pk>\d+)/pin/$', pin_topic, name='pin_topic'),

    re_path(r'(?P<slug>[\w.@+-]+)/topics/(?P<topic_pk>\d+)/reply/$', reply_topic, name='reply_topic'),
    re_path(r'(?P<slug>[\w.@+-]+)/topics/(?P<topic_pk>\d+)/posts/(?P<post_pk>\d+)/reply/$', reply_topic, name='reply_post'),
    re_path(r'(?P<slug>[\w.@+-]+)/topics/(?P<topic_pk>\d+)/posts/(?P<post_pk>\d+)/edit/$', PostUpdateView.as_view(), name='edit_post'),
    re_path(r'(?P<slug>[\w.@+-]+)/topics/(?P<topic_pk>\d+)/posts/(?P<post_pk>\d+)/delete/$', delete_post, name='delete_post'),
    re_path(r'(?P<slug>[\w.@+-]+)/topics/(?P<topic_pk>\d+)/posts/(?P<post_pk>\d+)/quote/$', quote_post, name='quote_post'),

#    path(r'search/', SearchResultsView.as_view(), name='search_results'),
    re_path('search', SearchResultsView.as_view(), name='search_results'),
]
