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
        if re.fullmatch(r"load '?[_a-zA-Z]'?;?", str, flags=re.IGNORECASE):
            return False
    return True


def sqllogic_commands_from_str(str):
    pattern = fr"^(?:{'|'.join(SQLLOGIC_COMMANDS)}).*$"
    sqllogic_commands_crude = re.findall(pattern, str, flags=(re.IGNORECASE | re.MULTILINE))
    sqllogic_commands = [cmd for cmd in sqllogic_commands_crude if verify_sqllocig_command(cmd)]
    return sqllogic_commands


def get_sql_statements(sqllogic_str: str):
    sqllogic_commands = sqllogic_commands_from_str(sqllogic_str)
    sql_statements = []

    # get sql statement per sqllogic command
    remainder = sqllogic_str
    sqllogic_command: str = ""
    for next_sqllogic_command in sqllogic_commands:
        lead, next_sqllogic_command, trail = remainder.partition(next_sqllogic_command)
        lead = lead.strip()
        if sqllogic_command.lower().startswith('statement'):
            sql_statements.append(lead)
        if sqllogic_command.lower().startswith('query'):
            sql_statement, _, _ = lead.partition("\n----")
            sql_statements.append(sql_statement)
        if sqllogic_command.lower().startswith('load'):
            pass
            # TODO: attach db file
        remainder = trail
        sqllogic_command = next_sqllogic_command.strip()
        # TODO: parse final trail (e.g. final CHECKPOINT;)
    for idx, sql in enumerate(sql_statements):
        if sql and sql[-1] != ';':
            sql_statements[idx] = sql + ";"
    return sql_statements
