# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

class Category(models.Model):
    title=models.CharField(max_length=100)
    def __str__(self):
        return self.title

class Post(models.Model):
    created_at=models.DateTimeField('date created')
    updated_at=models.DateTimeField('date updated')
    title=models.CharField(max_length=200)
    slug=models.SlugField(max_length=100)
    body=models.TextField(default="")
    category=models.ManyToManyField(Category)
    def __str__(self):
        return self.title