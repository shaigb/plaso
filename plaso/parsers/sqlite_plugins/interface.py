# -*- coding: utf-8 -*-
"""This file contains a SQLite parser."""

import logging
import sys

# pylint: disable=wrong-import-order
try:
  from pysqlite2 import dbapi2 as sqlite3
except ImportError:
  import sqlite3

from plaso.lib import errors
from plaso.parsers import plugins


class SQLitePlugin(plugins.BasePlugin):
  """A SQLite plugin for Plaso."""

  NAME = u'sqlite'
  DESCRIPTION = u'Parser for SQLite database files.'

  # Queries to be executed.
  # Should be a list of tuples with two entries, SQLCommand and callback
  # function name.
  QUERIES = []

  # List of tables that should be present in the database, for verification.
  REQUIRED_TABLES = frozenset([])

  @classmethod
  def _HashSQLiteRow(cls, row):
    """Hashes the given SQLite row.

    Args:
      row: A SQLite Row object (instance of sqlite3.Row)

    Returns:
      The hash value of the given row.
    """
    hash_value = 0
    for column_value in row:
      # In Python 2, blobs are "read-write buffer" and will cause a
      # "writable buffers are not hashable" error if we try to hash it.
      # Therefore, we will turn it into a string beforehand.
      if sys.version_info[0] < 3 and isinstance(column_value, buffer):
        column_value = str(column_value)
      hash_value ^= hash(column_value)
    return hash_value

  def GetEntries(
      self, parser_mediator, cache=None, database=None, database_wal=None,
      wal_file_entry=None, **unused_kwargs):
    """Extracts event objects from a SQLite database.

    Args:
      parser_mediator: A parser mediator object (instance of ParserMediator).
      cache: A SQLiteCache object.
      database: A database object (instance of SQLiteDatabase).
      database_wal: Optional database object with WAL file commited
                    (instance of SQLiteDatabase).
      wal_file_entry: Optional file entry for the database with committed WAL
                      file (instance of dfvfs.FileEntry).
    """
    for query, callback_method in self.QUERIES:
      try:
        callback = getattr(self, callback_method, None)
        if callback is None:
          logging.warning(
              u'[{0:s}] missing callback method: {1:s} for query: {2:s}'.format(
                  self.NAME, callback_method, query))
          continue

        sql_results = database.Query(query)
        if database_wal:
          wal_sql_results = database_wal.Query(query)
        else:
          wal_sql_results = None

        # Process database with WAL file.
        if database_wal and wal_sql_results:
          row_cache = set()
          for row in sql_results:
            callback(
                parser_mediator, row, query=query, cache=cache,
                database=database)
            row_cache.add(self._HashSQLiteRow(row))

          # Process unique rows in WAL file.
          file_entry = parser_mediator.GetFileEntry()
          parser_mediator.SetFileEntry(wal_file_entry)
          for row in wal_sql_results:
            if self._HashSQLiteRow(row) not in row_cache:
              callback(
                  parser_mediator, row, query=query, cache=cache,
                  database=database_wal)
          parser_mediator.SetFileEntry(file_entry)

        # Process database without WAL file.
        else:
          for row in sql_results:
            callback(
                parser_mediator, row, query=query, cache=cache,
                database=database)

      except sqlite3.DatabaseError as exception:
        logging.debug(
            u'SQLite error occurred: {0:s}'.format(exception))

  def Process(
      self, parser_mediator, cache=None, database=None, database_wal=None,
      wal_file_entry=None, **kwargs):
    """Determine if this is the right plugin for this database.

    This function takes a SQLiteDatabase object and compares the list
    of required tables against the available tables in the database.
    If all the tables defined in REQUIRED_TABLES are present in the
    database then this plugin is considered to be the correct plugin
    and the function will return back a generator that yields event
    objects.

    Args:
      parser_mediator: A parser mediator object (instance of ParserMediator).
      cache: A SQLiteCache object.
      database: A database object (instance of SQLiteDatabase).
      database_wal: Optional database object with WAL file committed
                    (instance of SQLiteDatabase).
      wal_file_entry: Optional file entry for the database with committed WAL
                      file (instance of dfvfs.FileEntry).

    Raises:
      errors.WrongPlugin: If the database does not contain all the tables
      defined in the REQUIRED_TABLES set.
      ValueError: If the database attribute is not passed in.
    """
    if database is None:
      raise ValueError(u'Database is not set.')

    if frozenset(database.tables) < self.REQUIRED_TABLES:
      raise errors.WrongPlugin(
          u'Not the correct database tables for: {0:s}'.format(self.NAME))

    # This will raise if unhandled keyword arguments are passed.
    super(SQLitePlugin, self).Process(parser_mediator)

    self.GetEntries(
        parser_mediator, cache=cache, database=database,
        database_wal=database_wal, wal_file_entry=wal_file_entry)
