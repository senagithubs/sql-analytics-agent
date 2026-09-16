"""Conservative SQLite query validation; execution also uses a read-only connection."""
from sqlglot import exp, parse
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.scope import traverse_scope


class UnsafeSQLError(ValueError):
    """The query is outside this demo's supported, read-only SQL subset."""


# SQLite function names used by the database authorizer. No extension/UDF calls.
SQLITE_FUNCTIONS = {
    'abs', 'avg', 'coalesce', 'count', 'date', 'datetime', 'ifnull', 'length',
    'lower', 'max', 'min', 'nullif', 'round', 'strftime', 'substr', 'substring',
    'sum', 'total', 'trim', 'upper', 'cast',
}
AST_FUNCTIONS = {s.upper() for s in SQLITE_FUNCTIONS} | {'CASE', 'IF', 'TIME_TO_STR', 'TS_OR_DS_TO_TIMESTAMP'}


def _nonnegative_integer(node):
    if not isinstance(node, exp.Literal) or not node.is_int or int(node.this) < 0:
        raise UnsafeSQLError('LIMIT/OFFSET must be a non-negative integer literal.')
    return int(node.this)


def validate_sql(sql: str, allowed_tables: set[str], max_limit: int = 1000) -> str:
    if isinstance(max_limit, bool) or not isinstance(max_limit, int) or max_limit <= 0:
        raise ValueError('max_limit must be a positive integer.')
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 10000:
        raise UnsafeSQLError('Provide a nonempty query shorter than 10,001 characters.')
    try:
        statements = parse(sql, read='sqlite')
        if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.SetOperation)):
            raise UnsafeSQLError('Exactly one SELECT query is supported.')
        query = statements[0]
        forbidden = (exp.DDL, exp.DML, exp.Command, exp.Into)
        if any(isinstance(n, forbidden) for n in query.walk()):
            raise UnsafeSQLError('Only read-only SELECT queries are supported.')
        if any(n.args.get('recursive') for n in query.find_all(exp.With)):
            raise UnsafeSQLError('Recursive CTEs are outside the demo scope.')
        allowed = {t.casefold() for t in allowed_tables}
        for scope in traverse_scope(query):
            for _, source in scope.selected_sources.values():
                if isinstance(source, exp.Table):
                    if not isinstance(source.this, exp.Identifier) or source.db or source.catalog:
                        raise UnsafeSQLError('Qualified tables and table functions are not supported.')
                    if source.name.casefold() not in allowed:
                        raise UnsafeSQLError(f'Table is not permitted: {source.name}')
        for function in query.find_all(exp.Func):
            name = function.name if isinstance(function, exp.Anonymous) else function.sql_name()
            if name.upper() not in AST_FUNCTIONS:
                raise UnsafeSQLError(f'Function is not supported: {name}')
        for limit in query.find_all(exp.Limit):
            _nonnegative_integer(limit.expression)
        for offset in query.find_all(exp.Offset):
            if _nonnegative_integer(offset.expression) > 10000:
                raise UnsafeSQLError('OFFSET exceeds the demo limit of 10,000.')
        outer_limit = query.args.get('limit')
        cap = min(_nonnegative_integer(outer_limit.expression), max_limit) if outer_limit else max_limit
        return query.limit(cap).sql(dialect='sqlite')
    except SqlglotError as exc:
        raise UnsafeSQLError('The SQLite query could not be parsed safely.') from exc
