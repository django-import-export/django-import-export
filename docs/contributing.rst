.. _contributing:

############
Contributing
############

django-import-export is open-source and, as such, grows (or shrinks) & improves in part
due to the community. Below are some guidelines on how to help with the project.

By contributing you agree to abide by the
`Code of Conduct <https://github.com/django-import-export/django-import-export/blob/main/CODE_OF_CONDUCT.md>`_.


Philosophy
----------

* django-import-export is BSD-licensed. All contributed code must be either

  * the original work of the author, contributed under the BSD, or...

  * work taken from another project released under a BSD-compatible license.

* GPL'd (or similar) works are not eligible for inclusion.

* django-import-export's git main branch should always be stable, production-ready & passing all tests.

.. _question:

Questions
---------

Please check the :ref:`common issues <common_issues>` section of the :doc:`FAQ <faq>` to see if your question already has an answer.

For general questions about usage, we recommend posting to Stack Overflow, using the
`django-import-export <https://stackoverflow.com/questions/tagged/django-import-export/>`_ tag.  Please search existing
answers to see if any match your problem.  If not, post a new question including as much relevant detail as you can.
See `how to ask <https://stackoverflow.com/help/how-to-ask/>`_ for more details.

For questions about the internals of the library, please raise an
`issue <https://github.com/django-import-export/django-import-export/issues/>`_ and use the 'question' workflow.

* First check to see if there is an existing issue which answers your question.

* Remember to include as much detail as you can so that your question is answered in a timely manner.

Guidelines For Reporting An Issue/Feature
-----------------------------------------

So you've found a bug or have a great idea for a feature. Here are the steps you should take to help get it
added/fixed in django-import-export:

* First, check to see if there's an existing
  `issue <https://github.com/django-import-export/django-import-export/issues/>`_ or
  `pull request <https://github.com/django-import-export/django-import-export/pulls/>`_ for the bug/feature.

* If there isn't one there, please file an issue. The ideal report includes:

  * A description of the problem/suggestion.

  * How to recreate the bug.

  * If relevant, including the versions of your:

    * Python interpreter

    * Django

    * tablib version

    * django-import-export

    * Optionally any of the other dependencies involved

  * Ideally, creating a pull request with a (failing) test case demonstrating what's wrong. This makes it easy for us
    to reproduce and fix the problem.

Guidelines For Contributing Code
--------------------------------

If you're ready to take the plunge and contribute back some code or documentation please consider the following:

* Search existing issues and PRs to see if there are already any similar proposals.

* For substantial changes, we recommend raising a question_ first so that we can offer any advice or pointers based on
  previous experience.

The process should look like:

* Fork the project on GitHub into your own account.

* Clone your copy of django-import-export.

* Make a new branch in git & commit your changes there.

* Push your new branch up to GitHub.

* Again, ensure there isn't already an issue or pull request out there on it.

  * If there is and you feel you have a better fix, please take note of the issue number and mention it in your pull
    request.

* Create a new pull request (based on your branch), including what the problem/feature is, versions of your software
  and referencing any related issues/pull requests.

* We recommend setting up your editor to automatically indicate non-conforming styles (see `Development`_).

In order to be merged into django-import-export, contributions must have the following:

* A solid patch that:

  * is clear.

  * works across all supported versions of Python/Django.

  * follows the existing style of the code base (mostly PEP-8).

  * comments included as needed to explain why the code functions as it does

* A test case that demonstrates the previous flaw that now passes with the included patch.

* If it adds/changes a public API, it must also include documentation for those changes.

* Must be appropriately licensed (see `Philosophy`_).

* Adds yourself to the `AUTHORS`_ file.

If your contribution lacks any of these things, they will have to be added by a core contributor before being merged
into django-import-export proper, which may take substantial time for the all-volunteer team to get to.

.. _`AUTHORS`: https://github.com/django-import-export/django-import-export/blob/main/AUTHORS

.. _llm_contributions:

LLM-Assisted Contributions
--------------------------

You are welcome to use LLM coding assistants and agents to help with contributions. They are a tool like any other,
and the guidelines above apply to their output exactly as they apply to code you write by hand. We do ask that you
follow the additional guidance below.

Responsibility
^^^^^^^^^^^^^^

* You, not the LLM, are responsible for what you submit.

* Do not submit code you have not read and understood. Be ready to explain and discuss any line of the diff.

* Make sure the change really works. A passing test suite is necessary but not sufficient: the suite cannot cover
  every combination of resource options, field types, widgets, admin integrations and databases that users run in
  production.

* Prefer small, focused changes. Agents tend to bundle a lint fix, a refactor and a feature into one pull request.
  Split them, so each can be reviewed and reverted on its own.

Disclosure
^^^^^^^^^^

* If an LLM wrote a substantial part of the change, say so in the pull request description. This is not a mark
  against the contribution. It tells reviewers where to look, since generated changes tend to be correct on the
  paths the tests exercise and wrong at the edges they do not.

* If the description claims that existing behaviour is unchanged, state which configurations you verified this
  against yourself (for example: which ``Resource`` options, ``skip_unchanged`` / ``use_bulk`` / ``use_transactions``
  settings, custom widgets, or admin workflows). "All tests pass" does not answer this question.

Communication
^^^^^^^^^^^^^

* Please do not use an LLM to speak for you in issues, pull requests or discussions, beyond translation or grammar
  help. Write your own pull request description, changelog entry and replies to review comments. Human-to-human
  communication is how a volunteer project works, and a description you had to write yourself is the best check that
  you understand the change.

* Do not replace or remove the pull request template.

Autonomous submissions
^^^^^^^^^^^^^^^^^^^^^^

* Agents that write code and open pull requests without a human reviewing the result first are not permitted.

* Pull requests that are mostly generated with little human input, or whose author cannot discuss the change, will be
  closed. In persistent cases they will be treated as spam.

New contributors
^^^^^^^^^^^^^^^^

* Issues labelled `good first issue`_ are set aside for people learning the codebase. Having an LLM produce a
  complete solution to one does not help anyone learn. Please leave them for that purpose, and pick a different
  issue if you are working mainly with an agent.

.. _`good first issue`: https://github.com/django-import-export/django-import-export/labels/good%20first%20issue

Development
-----------

Formatting
^^^^^^^^^^

* All files should be formatted using the black auto-formatter. This will be run by pre-commit if configured.

* The project repository includes an ``.editorconfig`` file. We recommend using a text editor with EditorConfig support
  to avoid indentation and whitespace issues.

* We allow up to 88 characters as this is the line length used by black. This check is included when you run flake8.
  Documentation, comments, and docstrings should be wrapped at 79 characters, even though PEP 8 suggests 72.

* To install pre-commit::

    python -m pip install pre-commit

  Then run::

    pre-commit install

* If using ``git blame``, you can ignore commits which made large changes to the code base, such as reformatting.
  Run this command from the base project directory::

    git config blame.ignoreRevsFile .git-blame-ignore-revs

.. _create_venv:

Create virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you have cloned and checked out the repository, you can install a new development environment as follows::

  python -m venv django-import-export-venv
  source django-import-export-venv/bin/activate
  python -m pip install '.[tests]'

Run tests
^^^^^^^^^

You can run the test suite with::

  make clean test

Build documentation
^^^^^^^^^^^^^^^^^^^

To build a local version of the documentation::

  python -m pip install -r requirements/docs.txt
  make build-html-doc

The documentation will be present in ``docs/_build/html/index.html``.

Translation
^^^^^^^^^^^

When generating or updating translation files with makemessages, use the `make messages <https://github.com/django-import-export/django-import-export/blob/c84e661ca4f26787f86de56f4ed546315913faab/Makefile#L33>`_
command. This command adds the
`--add-location=file <https://docs.djangoproject.com/en/dev/ref/django-admin/#cmdoption-makemessages-add-location>`_
arg to include only the source file path, not line numbers.

This keeps .po files cleaner and avoids unnecessary version control churn when line numbers shift due to
unrelated code changes.

Translators can still trace strings back to their source using the file references.
