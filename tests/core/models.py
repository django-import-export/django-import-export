from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)
    birthday = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name


class Book(models.Model):
    name = models.CharField('Book name', max_length=100)
    author = models.ForeignKey(Author, blank=True, null=True)
    author_email = models.EmailField('Author email', max_length=75, blank=True)
    imported = models.BooleanField(default=False)
    published = models.DateField('Published', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True,
            blank=True)
    categories = models.ManyToManyField(Category, blank=True)

    def __unicode__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField('auth.User')


class Entry(models.Model):
    user = models.ForeignKey('auth.User')
