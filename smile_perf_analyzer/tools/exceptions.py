# -*- coding: utf-8 -*-

from six import string_types
from xmlrpc.client import Fault

from odoo.exceptions import except_orm
from odoo.tools import ustr


def get_exception_message(e):
    e = e or ''
    if isinstance(e, string_types):
        return ustr(e)
    if isinstance(e, except_orm):
        return ustr(e.value)
    if isinstance(e, Fault):
        return ustr(e.faultString)
    return ustr(e.message)
