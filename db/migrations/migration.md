# Migration

DDL lives or structure change is in migration files rather than `schema.sql`: `schema.sql` stays the source of truth for the pods table and its FTS index,

New things are to be only added via migrations and thats the recommended approach to avoid schema drift. If you need to change an existing table, you can create a new migration that alters the table.