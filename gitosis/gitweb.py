"""
Generate ``gitweb`` project list based on ``gitosis.conf``.

To plug this into ``gitweb``, you have two choices.

- The global way, edit ``/etc/gitweb.conf`` to say::

	$projects_list = "/path/to/your/projects.list";

  Note that there can be only one such use of gitweb.

- The local way, create a new config file::

	do "/etc/gitweb.conf" if -e "/etc/gitweb.conf";
	$projects_list = "/path/to/your/projects.list";
        # see ``repositories`` in the ``gitosis`` section
        # of ``~/.gitosis.conf``; usually ``~/repos``
        # but you need to expand the tilde here
	$projectroot = "/path/to/your/repos";

   Then in your web server, set environment variable ``GITWEB_CONFIG``
   to point to this file.

   This way allows you have multiple separate uses of ``gitweb``, and
   isolates the changes a bit more nicely. Recommended.
"""

import os, urllib, logging

from ConfigParser import RawConfigParser, NoSectionError, NoOptionError

def _escape_filename(s):
    s = s.replace('\\', '\\\\')
    s = s.replace('$', '\\$')
    s = s.replace('"', '\\"')
    return s

def _getRepositoryDir(config):
    repositories = os.path.expanduser('~')
    try:
        path = config.get('gitosis', 'repositories')
    except (NoSectionError, NoOptionError):
        repositories = os.path.join(repositories, 'repositories')
    else:
        repositories = os.path.join(repositories, path)
    return repositories

def generate(config, fp):
    """
    Generate a config file and projects list for ``gitweb``.

    :param config: configuration to read projects from
    :type config: RawConfigParser

    :param fp: writable for ``projects.list``
    :type fp: (file-like, anything with ``.write(data)``)
    """
    log = logging.getLogger('gitosis.access.haveAccess')

    repositories = _getRepositoryDir(config)

    try:
        global_enable = config.getboolean('gitosis', 'gitweb')
    except (NoSectionError, NoOptionError):
        global_enable = False

    for section in config.sections():
        l = section.split(None, 1)
        type_ = l.pop(0)
        if type_ != 'repo':
            continue
        if not l:
            continue

        try:
            enable = config.getboolean(section, 'gitweb')
        except (NoSectionError, NoOptionError):
            enable = global_enable

        if not enable:
            continue

        name, = l

        if not os.path.exists(os.path.join(repositories, name)):
            namedotgit = '%s.git' % name
            if os.path.exists(os.path.join(repositories, namedotgit)):
                name = namedotgit
            else:
                log.warning(
                    'Cannot find %(name)r in %(repositories)r'
                    % dict(name=name, repositories=repositories))

        response = [name]
        try:
            owner = config.get(section, 'owner')
        except (NoSectionError, NoOptionError):
            pass
        else:
            response.append(owner)

        line = ' '.join([urllib.quote_plus(s) for s in response])
        print >>fp, line

def _getParser():
    import optparse
    parser = optparse.OptionParser(
        usage="%prog [--config=FILE] PROJECTSLIST")
    parser.set_defaults(
        config=os.path.expanduser('~/.gitosis.conf'),
        )
    parser.add_option('--config',
                      metavar='FILE',
                      help='read config from FILE (default %s)'
                      % parser.defaults['config'],
                      )
    return parser

def main():
    parser = _getParser()
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error('Expected one command line argument.')

    path, = args

    cfg = RawConfigParser()
    cfg.read(options.config)

    tmp = '%s.%d.tmp' % (path, os.getpid())

    f = file(tmp, 'w')
    try:
        generate(config=cfg, fp=f)
    finally:
        f.close()

    os.rename(tmp, path)