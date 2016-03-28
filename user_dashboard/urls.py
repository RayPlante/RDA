################################################################################
#
# File Name: urls.py
# Application: dashboard
# Purpose:
#
# Author: Sharief Youssef
#         sharief.youssef@nist.gov
#
#		  Xavier SCHMITT
#		  xavier.schmitt@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################

from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = patterns('',
    url(r'^$', 'user_dashboard.views.my_profile'),
    url(r'^my-profile$', 'user_dashboard.views.my_profile'),
    url(r'^my-profile/edit', 'user_dashboard.views.my_profile_edit'),
    url(r'^my-profile/change-password', 'user_dashboard.views.my_profile_change_password'),
    url(r'^forms', 'user_dashboard.views.dashboard_my_forms'),
    url(r'^resources$', 'user_dashboard.views.dashboard_resources'),
    url(r'^templates$', 'user_dashboard.views.dashboard_templates'),
    url(r'^types$', 'user_dashboard.views.dashboard_types'),
    url(r'^files$', 'user_dashboard.views.dashboard_files'),
    url(r'^toXML$', 'user_dashboard.ajax.dashboard_toXML'),
    url(r'^edit_information$', 'user_dashboard.ajax.edit_information'),
    url(r'^delete_object$', 'user_dashboard.ajax.delete_object'),
    url(r'^modules$', 'user_dashboard.views.dashboard_modules'),
    url(r'^detail$', 'user_dashboard.views.dashboard_detail_resource'),
    url(r'^delete_result', 'user_dashboard.ajax.delete_result'),
    url(r'^update_publish', 'user_dashboard.ajax.update_publish'),
    url(r'^update_unpublish', 'user_dashboard.ajax.update_unpublish'),
)+static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


urlpatterns += staticfiles_urlpatterns()