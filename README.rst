ao3.py
======

This is my fork of alexwlchan's ao3 package, which is not actively maintained. Contributors to this 
include etothepii and superborb. I actively maintain this fork and welcome contributions.

A departure from the original package is that this one uses your username and cookie,
rather than plaintext password entry. 

- verity (ladyofthelog)

**********

This Python package provides a scripted interface to some of the data on
`AO3 <https://archiveofourown.org/>`_ (the Archive of Our Own).

It is **not** an official API.

This package no longer is compatible with Py2.

Motivation
**********

I want to be able to write Python scripts that use data from AO3.

An official API for AO3 data has been `on the roadmap <http://archiveofourown.org/admin_posts/295>`_
for a couple of years.  Until that appears, I've cobbled together my own
page-scraping code that does the job.  It's a bit messy and fragile, but it
seems to work most of the time.

If/when we get the proper API, I'd drop this in a heartbeat and do it
properly.

- alexwlchan

Usage
*****

Create an API instance:

.. code-block:: pycon

   >>> from ao3 import AO3, 
   >>> api = AO3()
   
Logging into your account
--------------------------

Enter the contents of your _otwarchive_session cookie and username

.. code-block:: pycon

   >>> api.login('USERNAME',"COOKIE CONTENTS")
    
If you have Viewing History enabled, you can get a list of works from 
that history.

.. code-block:: pycon

   >>> rh=api.user.reading_history()
   >>> next(rh)
   
This returns a tuple with information about the next work in your history


Looking up information about a work
-----------------------------------

Getting a work:

.. code-block:: pycon

   >>> work = api.work(id='258626')

The ``id`` is the numeric portion of the URL.  For example, the work ID of
``https://archiveofourown.org/works/258626`` is ``258626``.

Get a URL:

.. code-block:: pycon

   >>> work.url
   'https://archiveofourown.org/works/258626'

You can then look up a number of attributes, similar to the Stats panel at the
top of a page.  Here's the full set you can look up:

.. code-block:: pycon

   >>> work.title
   'The Morning After'

   >>> work.author
   'ambyr'

   >>> work.summary
   "<p>Delicious just can't understand why it's the shy, quiet ones who get all the girls.</p>"

   >>> work.rating
   ['Teen And Up Audiences']

   >>> work.warnings
   []

(An empty list is synonymous with "No Archive Warnings", so that it's a falsey
value.)

.. code-block:: pycon

   >>> work.category
   ['F/M']

   >>> work.fandoms
   ['Anthropomorfic - Fandom']

   >>> work.relationship
   ['Pinboard/Fandom']

   >>> work.characters
   ['Pinboard', 'Delicious - Character', 'Diigo - Character']

   >>> work.additional_tags
   ['crackfic', 'Meta', 'so very not my usual thing']

   >>> work.language
   'English'

   >>> work.published
   datetime.date(2011, 9, 29)

   >>> work.words
   605

   >>> work.comments
   122

   >>> work.kudos
   1238

   >>> for name in work.kudos_left_by:
   ...     print(name)
   ...
   winterbelles
   AnonEhouse
   SailAweigh
   # and so on

   >>> work.bookmarks
   99

   >>> work.hits
   43037

There's also a method for dumping all the information about a work into JSON,
for easy export/passing into other places:

.. code-block:: pycon

   >>> work.json()
   '{"rating": ["Teen And Up Audiences"], "fandoms": ["Anthropomorfic - Fandom"], "characters": ["Pinboard", "Delicious - Character", "Diigo - Character"], "language": "English", "additional_tags": ["crackfic", "Meta", "so very not my usual thing"], "warnings": [], "id": "258626", "stats": {"hits": 43037, "words": 605, "bookmarks": 99, "comments": 122, "published": "2011-09-29", "kudos": 1238}, "author": "ambyr", "category": ["F/M"], "title": "The Morning After", "relationship": ["Pinboard/Fandom"], "summary": "<p>Delicious just can\'t understand why it\'s the shy, quiet ones who get all the girls.</p>"}'


Looking up your bookmarks
-------------------------

If you login as a user you can look up the bookmarks for that user. You can 
get the bookmarks as a list of AO3 id numbers or as a list of work objects.

Warning: This is very slow as as the api has to go back and retrieve every 
page.

Get the bookmarks as works:

.. code-block:: pycon

   >>> for bookmark in api.user.bookmarks():
   ...     print(bookmark.title)
   ...
   'Story Name'
   'Fanfiction Title'
   'Read This Fic'
   # and so on

Get the bookmarks as a list of id numbers:

.. code-block:: pycon

   >>> for bookmark_id in api.user.bookmarks_ids():
   ...     print(bookmark_id)
   ...
   '123'
   '456'
   '789'
   # and so on



License
*******

The project is licensed under the MIT license.
