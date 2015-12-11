from __future__ import unicode_literals
import random
import string

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=100)
    birthday = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField('Book name', max_length=100)
    author = models.ForeignKey(Author, blank=True, null=True)
    author_email = models.EmailField('Author email', max_length=75, blank=True)
    imported = models.BooleanField(default=False)
    published = models.DateField('Published', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                                blank=True)
    categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField('auth.User')
    is_private = models.BooleanField(default=True)


class Entry(models.Model):
    user = models.ForeignKey('auth.User')


class WithDefault(models.Model):
    name = models.CharField('Default', max_length=75, blank=True,
                            default=lambda: 'foo_bar')


class WithDynamicDefault(models.Model):
    def random_name():
        chars = string.ascii_lowercase
        return ''.join(random.SystemRandom().choice(chars) for _ in range(100))

    name = models.CharField('Dyn Default', max_length=100,
            default=random_name)
