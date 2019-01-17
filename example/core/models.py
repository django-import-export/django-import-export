from __future__ import unicode_literals
import random
import string

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=100)
    birthday = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def full_clean(self, exclude=None, validate_unique=True):
        super(Author, self).full_clean(exclude, validate_unique)
        if exclude is None:
            exclude = []
        else:
            exclude = list(exclude)
        if 'name' not in exclude and self.name == '123':
            raise ValidationError({'name': "'123' is not a valid value"})


@python_2_unicode_compatible
class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField('Book name', max_length=100)
    author = models.ForeignKey(Author, blank=True, null=True, on_delete=models.CASCADE)
    author_email = models.EmailField('Author email', max_length=75, blank=True)
    imported = models.BooleanField(default=False)
    published = models.DateField('Published', blank=True, null=True)
    published_time = models.TimeField('Time published', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                                blank=True)
    categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Parent(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Child(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return '%s - child of %s' % (self.name, self.parent.name)
