################################################################################
#
# File Name: models.py
# Application: admin_mdcs
# Purpose:   
#
# Author: Sharief Youssef
#         sharief.youssef@nist.gov
#
#         Guillaume SOUSA AMARAL
#         guillaume.sousa@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################
from functools import wraps
from django.contrib.auth.models import Group
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url
from urlparse import urlparse
from django.utils import six
from django.core.exceptions import PermissionDenied
import mgi.rights as RIGHTS

# Create your models here.
def login_or_anonymous_perm_required(anonymous_permission, function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    def _check_group(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            request.has_anonymous_access = False
            if request.user.is_anonymous():
                access = Group.objects.filter(Q(name=RIGHTS.anonymous_group) & Q(permissions__name=anonymous_permission))
            else:
                access = request.user.is_authenticated()

            if access:
                return view_func(request, *args, **kwargs)
            else:
                path = request.build_absolute_uri()
                resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
                # If the login url is the same scheme and net location then just
                # use the path as the "next" url.
                login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
                current_scheme, current_netloc = urlparse(path)[:2]
                if ((not login_scheme or login_scheme == current_scheme) and
                        (not login_netloc or login_netloc == current_netloc)):
                    path = request.get_full_path()
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(
                    path, resolved_login_url, redirect_field_name)

        return wrapper
    return _check_group


def permission_required(perm, login_url=None, raise_exception=False, redirect_field_name=REDIRECT_FIELD_NAME):
    def _check_group(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if isinstance(perm, six.string_types):
                perms = (perm, )
            else:
                perms = perm

            if request.user.is_anonymous():
                access = Group.objects.filter(Q(name=RIGHTS.anonymous_group) & Q(permissions__name=perm))
            else:
                access = request.user.has_perms(perms)

            if access:
                return view_func(request, *args, **kwargs)
            else:
                # In case the 403 handler should be called raise the exception
                if raise_exception:
                    raise PermissionDenied
                else:
                    path = request.build_absolute_uri()
                    resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
                    # If the login url is the same scheme and net location then just
                    # use the path as the "next" url.
                    login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
                    current_scheme, current_netloc = urlparse(path)[:2]
                    if ((not login_scheme or login_scheme == current_scheme) and
                            (not login_netloc or login_netloc == current_netloc)):
                        path = request.get_full_path()
                    from django.contrib.auth.views import redirect_to_login
                    return redirect_to_login(
                        path, resolved_login_url, redirect_field_name)

        return wrapper
    return _check_group
