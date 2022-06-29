# Create Database

Create the database directory:

```shell
$ mkdir databases/postgres
```

Initialize the database:

```shell
$ initdb -D databases/postgres
```

Start the postgres server:

```shell
$ honcho start
```

Create the application database:

```shell
$ createdb cast_registry
```

Create the database user:

```shell
$ createuser cast_registry
```

Grant access for database to user:

```shell
$ psql -d cast_registry -c "GRANT ALL PRIVILEGES ON DATABASE cast_registry to cast_registry;"
```

Migrate:

```shell
$ python manage.py migrate
```
