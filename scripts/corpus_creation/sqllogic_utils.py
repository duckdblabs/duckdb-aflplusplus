import re

from statement_types import SQLLOGIC_COMMANDS


def verify_sqllocig_command(str: str):
    # prevent mixup
    # - sqllogic 'load' means attach a db
    # - sql 'LOAD' means extension load
    if str.lower().startswith('load'):
        # exclude SQL extension load statements;
        if ".duckdb_extension" in str:
            return False
        if str.endswith(';'):
            return False
        if re.fullmatch(r"load '?[._a-zA-Z]+'?;?", str, flags=re.IGNORECASE):
            return False
    # 'set' and 'reset' are both valid in both sqllogic and sql syntax, in practice it is only used as sql statement
    if str.lower().startswith('set'):
        return False
    if str.lower().startswith('reset'):
        return False
    return True


def sqllogic_commands_from_str(str):
    pattern = fr"^(?:{'|'.join(SQLLOGIC_COMMANDS)}) .*$"
    sqllogic_commands_crude = re.findall(pattern, str, flags=(re.IGNORECASE | re.MULTILINE))
    sqllogic_commands = [cmd for cmd in sqllogic_commands_crude if verify_sqllocig_command(cmd)]
    return sqllogic_commands


def sql_from_sqllogic_block(sqllogic_command: str, code_block: str):
    if sqllogic_command.lower().startswith('statement') or sqllogic_command.lower().startswith('query'):
        sql_statement, _, _ = code_block.partition("\n----")
        sql_statement = sql_statement.strip()
        if len(sql_statement) == 0:
            sql_statement = ";"
        # add semicolon (;) if missing
        if sql_statement[-1] != ';':
            sql_statement += ";"
        return sql_statement
    if sqllogic_command.lower().startswith('load'):
        # TODO: attach db file
        pass
    return None


# scrape sql statements from sqllogic file
def get_sql_statements(sqllogic_str: str):
    # sql-statements can not directly be scraped via regex because of multi-line nested statements that don't necessarily end with ';'
    # therefore, find the sqllogic commands first: the sql is in the code blocks in between
    sqllogic_commands = sqllogic_commands_from_str(sqllogic_str)

    # first sqllogic command
    if sqllogic_commands:
        sqllogic_command = sqllogic_commands.pop(0)
        # ignore parts preceeding the first sqllogic command
        _, _, remainder = sqllogic_str.partition(sqllogic_command)
    else:
        return []

    # get sql statement per sqllogic command
    sql_statements = []
    final = False
    while True:
        if sqllogic_commands:
            next_sqllogic_command = sqllogic_commands.pop(0)
            code_block, next_sqllogic_command, remainder = remainder.partition(next_sqllogic_command)
        else:
            final = True
            code_block = remainder
        sql_statement = sql_from_sqllogic_block(sqllogic_command, code_block)
        if sql_statement:
            sql_statements.append(sql_statement)
        if final:
            break
        sqllogic_command = next_sqllogic_command
    return sql_statements
