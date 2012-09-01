from collections import OrderedDict
import re


class Configurator(object):
    """Supports configuration files with subsections."""
    def __init__(self, config_object):
        self._confer = config_object
        self._read_only = config_object.read_only

        self._sections = OrderedDict()

        for section_name in self._confer.sections():
            match = re.match('(?P<section>.+) "(?P<subsection>.+)"$', section_name)
            if match:

                supersection_n = match.groupdict()['section']
                section_n = match.groupdict()['subsection']

                supersection = self._sections.setdefault(supersection_n, Section(supersection_n, self, read_only=self._read_only))

                section = supersection._subsections.setdefault(section_n, Section(section_name, self, read_only=self._read_only))

            else:
                section = self._sections.setdefault(section_name, Section(section_name, self, read_only=self._read_only))

            for value_name, value in self._confer._sections[section_name].iteritems():
                section._values[value_name] = value

    def add_section(self, section_name):
        self._confer.add_section(section_name)

        match = re.match('(?P<section>.+) "(?P<subsection>.+)"$', section_name)
        if match:

            supersection_n = match.groupdict()['section']
            section_n = match.groupdict()['subsection']

            supersection = self._sections.setdefault(supersection_n, Section(supersection_n, self, read_only=self._read_only))

            section = supersection._subsections.setdefault(section_n, Section(section_name, self, read_only=self._read_only))
        else:
            section = self._sections.setdefault(section_name, Section(section_name, self, read_only=self._read_only))

        return section

    def __getattr__(self, attr):
        if attr in self._sections:
            return self._sections[attr]

        return object.__getattribute__(self, attr)


class Section(object):
    """Dotted-syntax access to settings"""
    def __init__(self, name, configurator, read_only=False, parent=None):
        self._name = name
        self._configurator = configurator
        self._subsections = OrderedDict()
        self._values = OrderedDict()
        self._read_only = read_only
        self._parent = parent

    def add_section(self, section_name):
        if section_name in self._subsections:
            raise KeyError("There's already a section with that name.")

        self._subsections[section_name] = Section(section_name, parent=self)

    def set_value(self, value_name, value):
        if self._read_only:
            raise AttributeError("This is a read-only instance.")
        self._values[value_name] = value
        self._configurator._confer.set(self._name, value_name, value)
        self._configurator._confer.write()

    def __getattr__(self, attr):
        if attr in super(Section, self).__getattribute__('_subsections'):
            return super(Section, self).__getattribute__('_subsections')[attr]

        elif attr in super(Section, self).__getattribute__('_values'):
            return super(Section, self).__getattribute__('_values')[attr]

        return super(Section, self).__getattribute__(attr)

    def __setattr__(self, attr, value):
        try:
            if attr in self._subsections:
                raise RuntimeError("Can't overwrite subsections this way.")

            elif not attr.startswith('_'):
                if self._read_only:
                    raise RuntimeError("This is a read-only instance")

                self.set_value(attr, value)

            else:
                super(Section, self).__setattr__(attr, value)
        except AttributeError:
            super(Section, self).__setattr__(attr, value)

    def __repr__(self):
        return '<Section: {}>'.format(self._name)
