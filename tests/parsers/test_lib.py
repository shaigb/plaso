# -*- coding: utf-8 -*-
"""Parser related functions and classes for testing."""

from dfvfs.lib import definitions as dfvfs_definitions
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver as path_spec_resolver

from plaso.containers import events
from plaso.engine import knowledge_base
from plaso.formatters import manager as formatters_manager
from plaso.formatters import mediator as formatters_mediator
from plaso.parsers import interface
from plaso.parsers import mediator
from plaso.storage import fake_storage

from tests import test_lib as shared_test_lib


class ParserTestCase(shared_test_lib.BaseTestCase):
  """The unit test case for a parser."""

  def _GetEventObjects(self, event_generator):
    """Retrieves the event objects from the event generator.

    This function will extract event objects from a generator.

    Args:
      event_generator: the event generator as returned by the parser.

    Returns:
      A list of event objects (instances of EventObject).
    """
    test_events = []

    for event_object in event_generator:
      self.assertIsInstance(event_object, events.EventObject)
      # Every event needs to have its parser and pathspec fields set, so that
      # it's possible to trace its provenance.
      self.assertIsNotNone(event_object.pathspec)
      self.assertIsNotNone(event_object.parser)
      test_events.append(event_object)

    return test_events

  def _GetParserMediator(
      self, storage_writer, file_entry=None, knowledge_base_values=None,
      parser_chain=None):
    """Retrieves a parser mediator object.

    Args:
      storage_writer: a storage writer object (instance of StorageWriter).
      file_entry: optional dfVFS file_entry object (instance of dfvfs.FileEntry)
                  being parsed.
      knowledge_base_values: optional dict containing the knowledge base
                             values.
      parser_chain: Optional string containing the parsing chain up to this
                    point.

    Returns:
      A parser mediator object (instance of ParserMediator).
    """
    knowledge_base_object = knowledge_base.KnowledgeBase()
    if knowledge_base_values:
      for identifier, value in iter(knowledge_base_values.items()):
        knowledge_base_object.SetValue(identifier, value)

    parser_mediator = mediator.ParserMediator(
        storage_writer, knowledge_base_object)

    if file_entry:
      parser_mediator.SetFileEntry(file_entry)

    if parser_chain:
      parser_mediator.parser_chain = parser_chain

    return parser_mediator

  def _GetShortMessage(self, message_string):
    """Shortens a message string to a maximum of 80 character width.

    Args:
      message_string: the message string.

    Returns:
      The same short message string, if it is longer than 80 characters it will
      be shortened to it's first 77 characters followed by a "...".
    """
    if len(message_string) > 80:
      return u'{0:s}...'.format(message_string[0:77])

    return message_string

  def _GetTestFileEntryFromPath(self, path_segments):
    """Creates a file entry that references a file in the test dir.

    Args:
      path_segments: the path segments inside the test data directory.

    Returns:
      A file entry object (instance of dfvfs.FileEntry).
    """
    path = self._GetTestFilePath(path_segments)
    path_spec = path_spec_factory.Factory.NewPathSpec(
        dfvfs_definitions.TYPE_INDICATOR_OS, location=path)
    return path_spec_resolver.Resolver.OpenFileEntry(path_spec)

  def _ParseFile(
      self, path_segments, parser_object, knowledge_base_values=None):
    """Parses a file using the parser object.

    Args:
      path_segments: a list of strings containinge the path segments inside
                     the test data directory.
      parser_object: a parser object (instance of BaseParser).
      knowledge_base_values: optional dict containing the knowledge base
                             values.

    Returns:
      A storage writer object (instance of FakeStorageWriter).
    """
    path = self._GetTestFilePath(path_segments)
    path_spec = path_spec_factory.Factory.NewPathSpec(
        dfvfs_definitions.TYPE_INDICATOR_OS, location=path)
    return self._ParseFileByPathSpec(
        path_spec, parser_object, knowledge_base_values=knowledge_base_values)

  def _ParseFileByPathSpec(
      self, path_spec, parser_object, knowledge_base_values=None):
    """Parses a file using the parser object.

    Args:
      path_spec: a path specification (instance of dfvfs.PathSpec).
      parser_object: a parser object (instance of BaseParser).
      knowledge_base_values: optional dictionary containing the knowledge base
                             values.

    Returns:
      A storage writer object (instance of FakeStorageWriter).
    """
    storage_writer = fake_storage.FakeStorageWriter()
    storage_writer.Open()

    file_entry = path_spec_resolver.Resolver.OpenFileEntry(path_spec)
    parser_mediator = self._GetParserMediator(
        storage_writer, file_entry=file_entry,
        knowledge_base_values=knowledge_base_values)

    if isinstance(parser_object, interface.FileEntryParser):
      parser_object.Parse(parser_mediator)

    elif isinstance(parser_object, interface.FileObjectParser):
      file_object = file_entry.GetFileObject()
      try:
        parser_object.Parse(parser_mediator, file_object)
      finally:
        file_object.close()

    else:
      self.fail(u'Got unsupported parser type: {0:s}'.format(
          type(parser_object)))

    return storage_writer

  def _TestGetMessageStrings(
      self, event_object, expected_message, expected_message_short):
    """Tests the formatting of the message strings.

       This function invokes the GetMessageStrings function of the event
       formatter on the event object and compares the resulting messages
       strings with those expected.

    Args:
      event_object: the event object (instance of EventObject).
      expected_message: the expected message string.
      expected_message_short: the expected short message string.
    """
    formatter_mediator = formatters_mediator.FormatterMediator(
        data_location=self._DATA_PATH)
    message, message_short = (
        formatters_manager.FormattersManager.GetMessageStrings(
            formatter_mediator, event_object))
    self.assertEqual(message, expected_message)
    self.assertEqual(message_short, expected_message_short)

  def _TestGetSourceStrings(
      self, event_object, expected_source, expected_source_short):
    """Tests the formatting of the source strings.

       This function invokes the GetSourceStrings function of the event
       formatter on the event object and compares the resulting source
       strings with those expected.

    Args:
      event_object: the event object (instance of EventObject).
      expected_source: the expected source string.
      expected_source_short: the expected short source string.
    """
    # TODO: change this to return the long variant first so it is consistent
    # with GetMessageStrings.
    source_short, source = (
        formatters_manager.FormattersManager.GetSourceStrings(event_object))
    self.assertEqual(source, expected_source)
    self.assertEqual(source_short, expected_source_short)
