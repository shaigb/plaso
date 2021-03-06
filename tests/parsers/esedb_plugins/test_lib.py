# -*- coding: utf-8 -*-
"""ESEDB plugin related functions and classes for testing."""

import pyesedb

from plaso.parsers import esedb
from plaso.storage import fake_storage

from tests.parsers import test_lib


class EseDbPluginTestCase(test_lib.ParserTestCase):
  """The unit test case for ESE database based plugins."""

  def _ParseEseDbFileWithPlugin(
      self, path_segments, plugin_object, knowledge_base_values=None):
    """Parses a file as an ESE database file and returns an event generator.

    Args:
      path_segments: a list of strings containinge the path segments inside
                     the test data directory.
      plugin_object: an ESE database plugin object (instance of EseDbPlugin).
      knowledge_base_values: optional dictionary containing the knowledge base
                             values.

    Returns:
      A storage writer object (instance of FakeStorageWriter).
    """
    storage_writer = fake_storage.FakeStorageWriter()
    storage_writer.Open()

    file_entry = self._GetTestFileEntryFromPath(path_segments)
    parser_mediator = self._GetParserMediator(
        storage_writer, file_entry=file_entry,
        knowledge_base_values=knowledge_base_values)

    file_object = file_entry.GetFileObject()

    try:
      esedb_file = pyesedb.file()
      esedb_file.open_file_object(file_object)
      cache = esedb.EseDbCache()
      plugin_object.Process(parser_mediator, cache=cache, database=esedb_file)
      esedb_file.close()

    finally:
      file_object.close()

    return storage_writer
