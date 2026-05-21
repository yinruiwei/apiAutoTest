from enum import StrEnum, unique


@unique
class SqlType(StrEnum):
    select = 'SELECT'
    insert = 'INSERT'
    update = 'UPDATE'
    delete = 'DELETE'
