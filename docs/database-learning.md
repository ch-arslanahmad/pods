# Databases Learning

## Indexes

Indexes in a database are like in an array.
They basically allow access to data in a more efficient way.

- Without an index, the database has to scan through all the data to find what it needs.
- With an index, it can quickly jump to the relevant data.

In a database, Indexes are created on specific columns (e.g., `id`, `name`) of a table, and they store a sorted copy of those columns and hence should be unique and hence are mostly primary keys (unique).

```sql

CREATE INDEX idx_pods_category ON pods(category);

-- syntax: CREATE INDEX index_name ON table_name(column_name);

DROP INDEX idx_test_category -- delete an index

```

Convention for index names is usually `idx_tablename_columnname`.

## FTS5

> [!important]
> FTS5 is SQLite-specific however the idea is implmented in other popular DBs as well. the other popular DBs:
> - Postgres has `tsvector` and `tsquery` & has the most powerful implementation available.
> - MySQL has `MATCH`.

**FTS = Full Text Search.**

FTS is a feature in a databases that allows search inside a column data, acting as a search engine inside inside a column of a table, used to search for specific keywords/phrases in large text data.

While, Normal search  = exact.

It allows exact + partial matches, ranked by relevance, however it is not a substring/fuzzy search, it is more of a keyword search. It breaks the text into tokens and searches for those tokens.

## Virtual Tables

A virtual table is a view (a stored query) that can be queried like a regular table. 

For example,
You have, Students, Subjects.

Then you have a virtual Grade Table that calculates the grade of each student in each subject based on their scores. This Grade Table is not actually stored in the database, but it can be queried like a regular table.

Another name for this is called a "view". 

In SQLite, however virtual table is not a "view", it is a table whose behavior is fully controlled by a module instead of SQLite's default engine.

We will use SQLite's FTS5 engine to create a virtual table for full-text search (FTS5).

In other languages, this concept is not called a view or virtual table rather they have their own implementation for this concept of handing the management of data to a module.

- In Postgres, you can call specific type of `extension` Foreign Data Wrappers (FDW).
- In MySQL/MariaSQL, you can use modules called `storage engines` to achieve similar functionality.








