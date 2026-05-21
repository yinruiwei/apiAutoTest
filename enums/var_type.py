from enum import StrEnum, unique


@unique
class VarType(StrEnum):
    CACHE = 'cache'
    ENV = 'env'
    GLOBAL = 'global'
