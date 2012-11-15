from django.db import models


class Book(models.Model):
    name = models.CharField('Book name', max_length=100)
    author_email = models.EmailField('Author email', max_length=75, blank=True)

    def __unicode__(self):
        return self.name
