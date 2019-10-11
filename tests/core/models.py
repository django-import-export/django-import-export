import random
import string

from django.core.exceptions import ValidationError
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)
    birthday = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def full_clean(self, exclude=None, validate_unique=True):
        super().full_clean(exclude, validate_unique)
        if exclude is None:
            exclude = []
        else:
            exclude = list(exclude)
        if 'name' not in exclude and self.name == '123':
            raise ValidationError({'name': "'123' is not a valid value"})


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    def __str__(self):
        return self.name


class Book(models.Model):
    name = models.CharField('Book name', max_length=100)
    author = models.ForeignKey(Author, blank=True, null=True, on_delete=models.CASCADE)
    author_email = models.EmailField('Author email', max_length=75, blank=True)
    imported = models.BooleanField(default=False)
    published = models.DateField('Published', blank=True, null=True)
    published_time = models.TimeField('Time published', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    added = models.DateTimeField(blank=True, null=True)

    categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return self.name


class Parent(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Child(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return '%s - child of %s' % (self.name, self.parent.name)


class Profile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    is_private = models.BooleanField(default=True)


class Entry(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)


class Role(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, null=True)


class Person(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)


class WithDefault(models.Model):
    name = models.CharField('Default', max_length=75, blank=True,
                            default='foo_bar')


def random_name():
    chars = string.ascii_lowercase
    return ''.join(random.SystemRandom().choice(chars) for _ in range(100))


class WithDynamicDefault(models.Model):

    name = models.CharField('Dyn Default', max_length=100,
            default=random_name)


class WithFloatField(models.Model):
    f = models.FloatField(blank=True, null=True)


class EBook(Book):
    """Book proxy model to have a separate admin url access and name"""
    class Meta:
        proxy = True
