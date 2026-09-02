.. bb:step:: Git

.. _Step-Git:

Git
+++

.. py:class:: buildbot.steps.source.git.Git

The :bb:step:`Git` build step clones or updates a `Git <http://git.or.cz/>`_ repository and checks out the specified branch or revision.

.. note::

   Buildbot supports Git version 1.2.0 or later.

.. code-block:: python

   from buildbot.plugins import steps

   factory.addStep(steps.Git(repourl='git://path/to/repo', mode='full',
                             method='clobber', submodules=True))

The Git step takes the following arguments:

``repourl`` (required)
   The URL of the upstream Git repository.

``port`` (optional, default: ``22``)
   The SSH port of the Git server.

``branch`` (optional, default: ``HEAD``)
   This specifies the name of the branch or the tag to use when a Build does not provide one of its own.
   If this parameter is not specified, and the Build does not provide a branch, the default branch of the remote repository will be used.
   If ``alwaysUseLatest`` is ``True`` then the branch and revision information that comes with the Build is ignored and the branch specified in this parameter is used.

``submodules`` (optional, default: ``False``)
   When initializing/updating a Git repository, this tells Buildbot whether to handle Git submodules.
   If ``remoteSubmodules`` is ``True``, then this tells Buildbot to use remote submodules: `Git Remote Submodules <https://git-scm.com/docs/git-submodule#Documentation/git-submodule.txt---remote>`_

``tags`` (optional, default: ``False``)
    Download tags in addition to the requested revision when updating repository.

``shallow`` (optional)
   Instructs Git to attempt shallow clones (``--depth 1``).
   The depth defaults to 1 and can be changed by passing an integer instead of ``True``.
   This option can be used only in incremental builds, or full builds with clobber method.

``reference`` (optional)
   Use the specified string as a path to a reference repository on the local machine.
   Git will try to grab objects from this path first instead of the main repository, if they exist.
   This option is mutually exclusive with ``shared_cache``, which maintains such a repository for you.

``shared_cache`` (optional, default: ``False``)
   When set to ``True``, Buildbot maintains one bare Git object cache per repository on each worker and lets every builder on that worker read objects from it through Git's alternates mechanism.
   Builders that share a worker then stop keeping private copies of the same history, which saves disk space and makes new checkouts faster because most objects are already present locally.
   The cache lives at ``<worker-basedir>/.git-cache/<hash>.git``, where the hash is the first 16 hex digits of the SHA-256 of the cache identity.

   .. code-block:: python

      from buildbot.plugins import steps

      factory.addStep(steps.Git(repourl='https://example.org/repo.git',
                                mode='full', method='fresh',
                                shared_cache=True))

   Enabling the option makes the first build on a worker slower, because Buildbot populates the cache with the repository's full history before the checkout runs.
   The worker needs room for that cache in addition to its existing work directories, which keep the objects they already have.
   A string value specifies a custom cache path instead of the default one.

   This option requires Git 2.12.0 or later.
   On older versions Buildbot does not create, update, or activate a shared cache, and new checkouts use the normal cache-free path.
   If an existing checkout already has a Buildbot-managed alternate from an earlier build, Buildbot preserves it to avoid removing access to borrowed objects, so keep that cache available until the checkout is clobbered or recreated.
   It needs no particular worker version, except that detecting a worker started with ``--delete-leftover-dirs`` requires worker 3.6.0 or later.
   ``shared_cache`` and ``reference`` are mutually exclusive.
   The cache applies only to the top-level repository: submodule object databases and Git LFS payloads are not shared.

   Cache identity and credentials
      The cache identity uses a lowercase scheme and drops a port that is the default for it, so ``git@host:repo``, ``ssh://git@host/repo`` and ``ssh://git@host:22/repo`` share one cache; other spelling differences, such as a non-default port or a trailing slash, select different caches.
      For HTTP and HTTPS URLs, URL userinfo is removed from the cache identity and the cache's ``origin`` URL.
      For other schemes the username is kept, so ``ssh://alice@host/repo`` and ``ssh://bob@host/repo`` use separate caches.
      Credentials supplied through ``auth_credentials`` or ``git_credentials`` are also not part of the cache identity.
      Consequently, ``shared_cache=True`` makes all credentials used with the same credential-free repository URL share one object store.
      Enabling this mode asserts that those credentials expose the same repository object graph and are permitted to share objects.
      If authentication can expose different objects for the same URL, configure a distinct string ``shared_cache`` path for each credential scope.
      The configured ``repourl`` and credentials are still used for network fetches.
      HTTP and HTTPS repository URLs containing a query or fragment are rejected when shared caching is enabled because Buildbot cannot safely distinguish repository identity parameters from credentials that must not be persisted.
      This restriction does not apply when ``shared_cache`` is disabled.
      Relative local file-system paths are not supported as ``repourl`` when ``shared_cache`` is enabled; use an absolute local path or a repository URL.
      On Windows, a local ``repourl`` must likewise be fully qualified; drive-relative, current-drive-rooted, and incomplete UNC paths are rejected.
      This does not affect relative string values for ``shared_cache`` itself, which are resolved from the worker base directory as described above.

``origin`` (optional)
   By default, any clone will use the name "origin" as the remote repository (eg, "origin/master").
   This renderable option allows that to be configured to an alternate name.

``filters`` (optional, type: ``list``)
   For each string in the passed in list, adds a ``--filter <filter>`` argument to :command:`git clone` and :command:`git fetch`.
   For existing repositories, Buildbot also configures the remote as a partial clone promisor remote before fetching.
   This allows for adding filters like ``--filter "tree:0"`` to speed up clone and fetch operations.
   This requires git version 2.27 or higher.

``progress`` (optional)
   Passes the (``--progress``) flag to (:command:`git fetch`).
   This solves issues of long fetches being killed due to lack of output, but requires Git 1.7.2 or later.
   Its value is True on Git 1.7.2 or later.

``retryFetch`` (optional, default: ``False``)
   If true, if the ``git fetch`` fails, then Buildbot retries to fetch again instead of failing the entire source checkout.

``clobberOnFailure`` (optional, default: ``False``)
   If a fetch or full clone fails, we can retry to checkout the source by removing everything and cloning the repository.
   If the retry fails, it fails the source checkout step.

``mode`` (optional, default: ``'incremental'``)
   Specifies whether to clean the build tree or not.

   ``incremental``
      The source is update, but any built files are left untouched.

   ``full``
      The build tree is clean of any built files.
      The exact method for doing this is controlled by the ``method`` argument.

``method`` (optional, default: ``fresh`` when mode is ``full``)
   Git's incremental mode does not require a method.
   The full mode has four methods defined:

   ``clobber``
      It removes the build directory entirely then makes full clone from repo.
      This can be slow as it need to clone whole repository.
      To make faster clones enable the ``shallow`` option.
      If the shallow option is enabled and the build request has unknown revision value, then this step fails.

   ``fresh``
      This removes all other files except those tracked by Git.
      First it does :command:`git clean -d -f -f -x`, then fetch/checkout to a specified revision (if any).
      This option is equal to update mode with ``ignore_ignores=True`` in old steps.

   ``clean``
      All the files which are tracked by Git, as well as listed ignore files, are not deleted.
      All other remaining files will be deleted before the fetch/checkout.
      This is equivalent to :command:`git clean -d -f -f` then fetch.
      This is equivalent to ``ignore_ignores=False`` in old steps.

   ``copy``
      This first checks out source into source directory, then copies the ``source`` directory to ``build`` directory, and then performs the build operation in the copied directory.
      This way, we make fresh builds with very little bandwidth to download source.
      The behavior of source checkout follows exactly the same as incremental.
      It performs all the incremental checkout behavior in ``source`` directory.

``getDescription`` (optional)
   After checkout, invoke a `git describe` on the revision and save the result in a property; the property's name is either ``commit-description`` or ``commit-description-foo``, depending on whether the ``codebase`` argument was also provided.
   The argument should either be a ``bool`` or ``dict``, and will change how `git describe` is called:

   * ``getDescription=False``: disables this feature explicitly
   * ``getDescription=True`` or empty ``{}``: runs `git describe` with no args
   * ``getDescription={...}``: a dict with keys named the same as the Git option.
     Each key's value can be ``False`` or ``None`` to explicitly skip that argument.

     For the following keys, a value of ``True`` appends the same-named Git argument:

      * ``all`` : `--all`
      * ``always``: `--always`
      * ``contains``: `--contains`
      * ``debug``: `--debug`
      * ``long``: `--long``
      * ``exact-match``: `--exact-match`
      * ``first-parent``: `--first-parent`
      * ``tags``: `--tags`
      * ``dirty``: `--dirty`

     For the following keys, an integer or string value (depending on what Git expects) will set the argument's parameter appropriately.
     Examples show the key-value pair:

      * ``match=foo``: `--match foo`
      * ``exclude=foo``: `--exclude foo`
      * ``abbrev=7``: `--abbrev=7`
      * ``candidates=7``: `--candidates=7`
      * ``dirty=foo``: `--dirty=foo`

``config`` (optional)
   A dict of Git configuration settings to pass to the remote Git commands.

``sshPrivateKey`` (optional)
   The private key to use when running Git for fetch operations.
   The ssh utility must be in the system path in order to use this option.
   On Windows, only Git distribution that embeds MINGW has been tested (as of July 2017, the official distribution is MINGW-based).
   The worker must either have the host in the known hosts file or the host key must be specified via the `sshHostKey` option.

``sshHostKey`` (optional)
   Specifies public host key to match when authenticating with SSH public key authentication.
   This may be either a :ref:`Secret` or just a string.
   `sshPrivateKey` must be specified in order to use this option.
   The host key must be in the form of `<key type> <base64-encoded string>`, e.g. `ssh-rsa AAAAB3N<...>FAaQ==`.

``sshKnownHosts`` (optional)
   Specifies the contents of the SSH known_hosts file to match when authenticating with SSH public key authentication.
   This may be either a :ref:`Secret` or just a string.
   `sshPrivateKey` must be specified in order to use this option.
   `sshHostKey` must not be specified in order to use this option.

``auth_credentials``

   (optional) An username/password tuple to use when running git for fetch operations.
   The worker's git version needs to be at least 1.7.9.

``git_credentials``

   (optional) See :ref:`GitCredentialOptions`.
   The worker's git version needs to be at least 1.7.9.
