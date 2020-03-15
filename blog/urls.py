from django.conf.urls import url

from . import views

app_name = 'blog'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'contact/$', views.contact, name='contact'),
    url(r'^blog/$', views.blog_home, name='blog_home'),
    url(r'^blog/(?P<post_id>[0-9]+)/$', views.detail, name='detail')
]