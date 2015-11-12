################################################################################
#
# File Name: models.py
# Application: explore
# Purpose:   
#
# Author: Sharief Youssef
#         sharief.youssef@nist.gov
#
#         Guillaume Sousa Amaral
#         guillaume.sousa@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################
from django.db import models
import mgi.rights as RIGHTS


class Explore(models.Model):
    # model stuff here
    class Meta:
        permissions = (
            (RIGHTS.explore_access, RIGHTS.explore_access),
            (RIGHTS.explore_save_query, RIGHTS.explore_save_query),
            (RIGHTS.explore_delete_query, RIGHTS.explore_delete_query),
            (RIGHTS.explore_edit_document, RIGHTS.explore_edit_document),
            (RIGHTS.explore_delete_document, RIGHTS.explore_delete_document),
        )