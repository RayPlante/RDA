import urls
import re
from django.core.urlresolvers import RegexURLResolver, RegexURLPattern
from django.contrib.admindocs.views import simplify_regex
from mgi.models import Module
from mongoengine.errors import ValidationError
from modules.exceptions import ModuleError
    
def __assemble_endpoint_data__(pattern, prefix='', filter_path=None):
    """
    Creates a dictionary for matched API urls
    pattern -- the pattern to parse
    prefix -- the API path prefix (used by recursion)
    """
    path = simplify_regex(prefix + pattern.regex.pattern)
    
    if filter_path is not None:
        if re.match('^/?%s(/.*)?$' % re.escape(filter_path), path) is None:
            return None
    
    path = path.replace('<', '{').replace('>', '}')
    
    return {
        'url': path,
        'name': pattern.name,        
    }


def __flatten_patterns_tree__(patterns, prefix='', filter_path=None, exclude_namespaces=[]):
    """
    Uses recursion to flatten url tree.
    patterns -- urlpatterns list
    prefix -- (optional) Prefix for URL pattern
    """
    pattern_list = []
    
    for pattern in patterns:
        if isinstance(pattern, RegexURLPattern):
            endpoint_data = __assemble_endpoint_data__(pattern, prefix, filter_path=filter_path)
    
            if endpoint_data is None:
                continue
    
            pattern_list.append(endpoint_data)
    
        elif isinstance(pattern, RegexURLResolver):
    
            if pattern.namespace is not None and pattern.namespace in exclude_namespaces:
                continue
    
            pref = prefix + pattern.regex.pattern
            pattern_list.extend(__flatten_patterns_tree__(
                pattern.url_patterns,
                pref,
                filter_path=filter_path,
                exclude_namespaces=exclude_namespaces,
            ))
    
    return pattern_list


def discover_modules():
    patterns = __flatten_patterns_tree__(urls.urlpatterns)
    
    # Remove all existing modules
    Module.objects.all().delete()
    
    try:
        for pattern in patterns:
            Module(url=pattern['url'], name=pattern['name']).save()
    except ValidationError:
        raise ModuleError('A validation error occured during the module discovery. Please provide a name to all modules urls using the name argument.')
        # something went wrong, delete already added modules
        Module.objects.all().delete()
    except Exception, e:
        raise e
        # something went wrong, delete already added modules
        Module.objects.all().delete()