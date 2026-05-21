from enum import StrEnum, unique


@unique
class MethodType(StrEnum):
    get = 'GET'
    post = 'POST'
    put = 'PUT'
    delete = 'DELETE'
    patch = 'PATCH'
