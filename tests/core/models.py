import random
import string
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AuthorManager(models.Manager):
    """
    Used to enable the get_by_natural_key method.
    NOTE: Manager classes are only required to enable
    using the natural key functionality of ForeignKeyWidget
    """

    def get_by_natural_key(self, name):
        """
        Django pattern function for finding an author by its name
        """
        return self.get(name=name)


class Author(models.Model):
    objects = AuthorManager()

    name = models.CharField(max_length=100)
    birthday = models.DateTimeField(default=timezone.now)

    def natural_key(self):
        """
        Django pattern function for serializing a model by its natural key
        Used only by the ForeignKeyWidget using use_natural_foreign_keys.
        """
        return (self.name,)

    def __str__(self):
        return self.name

    def full_clean(self, exclude=None, validate_unique=True):
        super().full_clean(exclude, validate_unique)
        if exclude is None:
            exclude = []
        else:
            exclude = list(exclude)
        if "name" not in exclude and self.name == "123":
            raise ValidationError({"name": "'123' is not a valid value"})


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "categories"


class BookManager(models.Manager):
    """
    Added to enable get_by_natural_key method
    NOTE: Manager classes are only required to enable
    using the natural key functionality of ForeignKeyWidget
    """

    def get_by_natural_key(self, name, author):
        """
        Django pattern function for returning a book by its natural key
        """
        return self.get(name=name, author=Author.objects.get_by_natural_key(author))


class Book(models.Model):
    objects = BookManager()

    name = models.CharField("Book name", max_length=100)
    author = models.ForeignKey(Author, blank=True, null=True, on_delete=models.CASCADE)
    author_email = models.EmailField("Author email", max_length=75, blank=True)
    imported = models.BooleanField(default=False)
    published = models.DateField("Published", blank=True, null=True)
    published_time = models.TimeField("Time published", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    added = models.DateTimeField(blank=True, null=True)

    categories = models.ManyToManyField(Category, blank=True)

    def natural_key(self):
        """
        Django pattern function for serializing a book by its natural key.
        Used only by the ForeignKeyWidget using use_natural_foreign_keys.
        """
        return (self.name,) + self.author.natural_key()

    natural_key.dependencies = ["core.Author"]

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
        return f"{self.name} - child of {self.parent.name}"


class Profile(models.Model):
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE)
    is_private = models.BooleanField(default=True)


class Entry(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)


class Role(models.Model):
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, null=True)


class Person(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)


class WithDefault(models.Model):
    name = models.CharField("Default", max_length=75, blank=True, default="foo_bar")


def random_name():
    chars = string.ascii_lowercase
    return "".join(random.SystemRandom().choice(chars) for _ in range(100))


class WithDynamicDefault(models.Model):
    name = models.CharField("Dyn Default", max_length=100, default=random_name)


class WithFloatField(models.Model):
    f = models.FloatField(blank=True, null=True)


class EBook(Book):
    """Book proxy model to have a separate admin url access and name"""

    class Meta:
        proxy = True


class NamedAuthor(models.Model):
    """Class with a named primary key"""

    name = models.CharField(max_length=256, primary_key=True)


class UUIDCategory(models.Model):
    catid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "UUID categories"


class UUIDBook(models.Model):
    """A model which uses a UUID pk (issue 1274)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Book name", max_length=100)
    author = models.ForeignKey(
        NamedAuthor, blank=True, null=True, on_delete=models.CASCADE
    )
    categories = models.ManyToManyField(UUIDCategory, blank=True)

    def __str__(self):
        return self.name


class WithPositiveIntegerFields(models.Model):
    big = models.PositiveBigIntegerField(null=True)
    small = models.PositiveSmallIntegerField(null=True)
