from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name


class Book(models.Model):
    name = models.CharField('Book name', max_length=100)
    author = models.ForeignKey(Author, blank=True, null=True)
    author_email = models.EmailField('Author email', max_length=75, blank=True)
    imported = models.BooleanField(default=False)
    published = models.DateField('Published', blank=True, null=True)

    def __unicode__(self):
        return self.name
