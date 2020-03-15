# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404, render
from .models import Post

def blog_home(request):
    posts = Post.objects.order_by('-created_at')[:100]
    context = {'blogposts': posts}
    return render(request, 'blog/blog_home.html', context)

def index(request):
    return render(request, 'blog/index.html')

def contact(request):
    return render(request, 'blog/contact.html')


def detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    return render(request, 'blog/post.html', {'post': post})